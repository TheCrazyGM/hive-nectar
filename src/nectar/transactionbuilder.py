import logging
import struct
from binascii import unhexlify

# import time (not currently used)
from nectar.instance import shared_blockchain_instance
from nectarbase import operations
from nectarbase.ledgertransactions import Ledger_Transaction
from nectarbase.objects import Operation
from nectarbase.signedtransactions import Signed_Transaction
from nectargraphenebase.account import PrivateKey, PublicKey
from nectarstorage.exceptions import WalletLocked

from .account import Account
from .exceptions import (
    InsufficientAuthorityError,
    InvalidWifError,
    MissingKeyError,
    OfflineHasNoRPCException,
)
from .utils import formatTimeFromNow

log = logging.getLogger(__name__)


class TransactionBuilder(dict):
    """This class simplifies the creation of transactions by adding
    operations and signers.
    To build your own transactions and sign them

    :param dict tx: transaction (Optional). If not set, the new transaction is created.
    :param int expiration: Delay in seconds until transactions are supposed
        to expire *(optional)* (default is 30)
    :param Hive blockchain_instance: If not set, shared_blockchain_instance() is used

    .. testcode::

       from nectar.transactionbuilder import TransactionBuilder
       from nectarbase.operations import Transfer
       from nectar import Hive
       wif = "5KQwrPbwdL6PhXujxW37FSSQZ1JiwsST4cqQzDeyXtP79zkvFD3"
       hive = Hive(nobroadcast=True, keys={'active': wif})
       tx = TransactionBuilder(blockchain_instance=hive)
       transfer = {"from": "test", "to": "test1", "amount": "1 HIVE", "memo": ""}
       tx.appendOps(Transfer(transfer))
       tx.appendSigner("test", "active") # or tx.appendWif(wif)
       signed_tx = tx.sign()
       broadcast_tx = tx.broadcast()

    """

    def __init__(self, tx=None, blockchain_instance=None, **kwargs):
        """
        Initialize a TransactionBuilder, optionally from an existing transaction dict.

        If `tx` is a dict, its contents are loaded into the builder (operations are taken from tx["operations"])
        and reconstruction is marked as not required. Otherwise the builder starts empty and is marked to
        require reconstruction before use. The constructor clears any prior state, captures ledger/path and
        condenser API configuration from the provided blockchain instance (or the shared instance), and sets
        the transaction expiration from kwargs or the blockchain default.

        Parameters:
            tx (dict, optional): An existing transaction dictionary to load. When provided and valid,
                operations are initialized from tx["operations"] and reconstruction is disabled.
            expiration (int, optional, via kwargs): Transaction expiration (seconds or blockchain-specific
                expiration value). If omitted, the blockchain instance's default expiration is used.

        Notes:
            - The `blockchain_instance` parameter is a shared service/client and is intentionally not
              documented here beyond its effect on builder configuration.
        """
        self.blockchain = blockchain_instance or shared_blockchain_instance()
        self.clear()
        if tx and isinstance(tx, dict):
            super().__init__(tx)
            # Load operations
            self.ops = tx["operations"]
            self._require_reconstruction = False
        else:
            self._require_reconstruction = True
        self._use_ledger = self.blockchain.use_ledger
        self.path = self.blockchain.path
        self._use_condenser_api = bool(self.blockchain.config["use_condenser"])
        self.set_expiration(kwargs.get("expiration", self.blockchain.expiration))

    def set_expiration(self, p):
        """Set expiration date"""
        self.expiration = p

    def is_empty(self):
        """Check if ops is empty"""
        return not (len(self.ops) > 0)

    def list_operations(self):
        """List all ops"""
        appbase = not self._use_condenser_api
        return [Operation(o, appbase=appbase, prefix=self.blockchain.prefix) for o in self.ops]

    def _is_signed(self):
        """Check if signatures exists"""
        return "signatures" in self and bool(self["signatures"])

    def _is_constructed(self):
        """Check if tx is already constructed"""
        return "expiration" in self and bool(self["expiration"])

    def _is_require_reconstruction(self):
        return self._require_reconstruction

    def _set_require_reconstruction(self):
        self._require_reconstruction = True

    def _unset_require_reconstruction(self):
        self._require_reconstruction = False

    def _get_auth_field(self, permission):
        return permission

    def __repr__(self):
        return "<Transaction num_ops={}, ops={}>".format(
            len(self.ops), [op.__class__.__name__ for op in self.ops]
        )

    def __str__(self):
        return str(self.json())

    def __getitem__(self, key):
        if key not in self:
            self.constructTx()
        return dict(self).__getitem__(key)

    def get_parent(self):
        """TransactionBuilders don't have parents, they are their own parent"""
        return self

    def json(self, with_prefix=False):
        """Show the transaction as plain json"""
        if not self._is_constructed() or self._is_require_reconstruction():
            self.constructTx()
        json_dict = dict(self)
        if with_prefix:
            json_dict["prefix"] = self.blockchain.prefix
        return json_dict

    def appendOps(self, ops, append_to=None):
        """Append op(s) to the transaction builder

        :param list ops: One or a list of operations
        """
        if isinstance(ops, list):
            self.ops.extend(ops)
        else:
            self.ops.append(ops)
        self._set_require_reconstruction()

    def _fetchkeys(self, account, perm, level=0, required_treshold=1):
        # Do not travel recursion more than 2 levels
        if level > 2:
            return []

        r = []
        wif = None
        # Let's go through all *keys* of the account
        for authority in account[perm]["key_auths"]:
            try:
                # Try obtain the private key from wallet
                wif = self.blockchain.wallet.getPrivateKeyForPublicKey(authority[0])
            except ValueError:
                pass
            except MissingKeyError:
                pass

            if wif:
                r.append([wif, authority[1]])
                # If we found a key for account, we add it
                # to signing_accounts to be sure we do not resign
                # another operation with the same account/wif
                self.signing_accounts.append(account)

            # Test if we reached threshold already
            if sum([x[1] for x in r]) >= required_treshold:
                break

        # Let's see if we still need to go through accounts
        if sum([x[1] for x in r]) < required_treshold:
            # go one level deeper
            for authority in account[perm]["account_auths"]:
                # Let's see if we can find keys for an account in
                # account_auths
                # This is recursive with a limit at level 2 (see above)
                auth_account = Account(authority[0], blockchain_instance=self.blockchain)
                required_treshold = auth_account[perm]["weight_threshold"]
                keys = self._fetchkeys(auth_account, perm, level + 1, required_treshold)

                for key in keys:
                    r.append(key)

                    # Test if we reached threshold already and break
                    if sum([x[1] for x in r]) >= required_treshold:
                        break

        return r

    def appendSigner(self, account, permission):
        """
        Register an account as a signer for this transaction by locating or assigning the needed signing keys.

        Attempts to resolve signing credentials for `account` at the requested `permission` and attaches them to the builder state. Behavior varies by signing mode:
        - Ledger mode: verifies that the ledger-derived public key for the currently selected path is authorized for the account/permission (raises AssertionError if not).
        - Wallet mode: fetches private keys from the local wallet and stores corresponding WIFs; if the account argument is a PublicKey, the matching WIF is retrieved and added.

        Parameters:
            account (str | Account | PublicKey): account name, Account instance, or public key identifying the signer.
            permission (str): permission level to use ("active", "owner", or "posting").

        Raises:
            WalletLocked: if the local wallet is locked when wallet keys are required.
            AssertionError: for invalid permission values, if the requested permission cannot be accessed, or if a ledger public key is not found in the account authorities.
        """
        if not self.blockchain.is_connected():
            return
        if permission not in ["active", "owner", "posting"]:
            raise AssertionError("Invalid permission")
        account = Account(account, blockchain_instance=self.blockchain)
        auth_field = self._get_auth_field(permission)
        if auth_field not in account:
            account = Account(account, blockchain_instance=self.blockchain, lazy=False, full=True)
            account.clear_cache()
            account.refresh()
        if auth_field not in account:
            account = Account(account, blockchain_instance=self.blockchain)
        if auth_field not in account:
            raise AssertionError("Could not access permission")

        if self._use_ledger:
            if not self._is_constructed() or self._is_require_reconstruction():
                self.constructTx()

            key_found = False
            if self.path is not None:
                current_pubkey = self.ledgertx.get_pubkey(self.path)
                for authority in account[auth_field]["key_auths"]:
                    if str(current_pubkey) == authority[0]:
                        key_found = True
                if permission == "posting" and not key_found:
                    for authority in account["active"]["key_auths"]:
                        if str(current_pubkey) == authority[0]:
                            key_found = True
                if not key_found:
                    for authority in account["owner"]["key_auths"]:
                        if str(current_pubkey) == authority[0]:
                            key_found = True
            if not key_found:
                raise AssertionError(
                    "Could not find pubkey from {} in path: {}!".format(account["name"], self.path)
                )
            return

        if self.blockchain.wallet.locked():
            raise WalletLocked()

        if account["name"] not in self.signing_accounts:
            # is the account an instance of public key?
            if isinstance(account, PublicKey):
                self.wifs.add(self.blockchain.wallet.getPrivateKeyForPublicKey(str(account)))
            else:
                if auth_field not in account:
                    raise AssertionError("Could not access permission")
                required_treshold = account[auth_field]["weight_threshold"]
                keys = self._fetchkeys(account, permission, required_treshold=required_treshold)
                # If keys are empty, try again with active key
                if not keys and permission == "posting":
                    _keys = self._fetchkeys(account, "active", required_treshold=required_treshold)
                    keys.extend(_keys)
                # If keys are empty, try again with owner key
                if not keys and permission != "owner":
                    _keys = self._fetchkeys(account, "owner", required_treshold=required_treshold)
                    keys.extend(_keys)
                for x in keys:
                    self.appendWif(x[0])

            self.signing_accounts.append(account["name"])

    def appendWif(self, wif):
        """Add a wif that should be used for signing of the transaction.

        :param string wif: One wif key to use for signing
            a transaction.
        """
        if wif:
            try:
                PrivateKey(wif, prefix=self.blockchain.prefix)
                self.wifs.add(wif)
            except Exception:
                raise InvalidWifError

    def clearWifs(self):
        """Clear all stored wifs"""
        self.wifs = set()

    def setPath(self, path):
        self.path = path

    def searchPath(self, account, perm):
        if not self.blockchain.use_ledger:
            return
        if not self._is_constructed() or self._is_require_reconstruction():
            self.constructTx()
        key_found = False
        path = None
        current_account_index = 0
        current_key_index = 0
        while not key_found and current_account_index < 5:
            path = self.ledgertx.build_path(perm, current_account_index, current_key_index)
            current_pubkey = self.ledgertx.get_pubkey(path)
            key_found = False
            for authority in account[perm]["key_auths"]:
                if str(current_pubkey) == authority[1]:
                    key_found = True
            if not key_found and current_key_index < 5:
                current_key_index += 1
            elif not key_found and current_key_index >= 5:
                current_key_index = 0
                current_account_index += 1
        if not key_found:
            return None
        else:
            return path

    def constructTx(self, ref_block_num=None, ref_block_prefix=None):
        """Construct the actual transaction and store it in the class's dict
        store

        """
        ops = list()
        appbase = not self._use_condenser_api
        for op in self.ops:
            # otherwise, we simply wrap ops into Operations
            ops.extend([Operation(op, appbase=appbase, prefix=self.blockchain.prefix)])

        # calculation expiration time from last block time not system time
        # it fixes transaction expiration error when pushing transactions
        # when blocks are moved forward with debug_produce_block*
        # Prefer chain head time when connected to align with node clock and avoid expiration drift
        exp_seconds = int(self.expiration or self.blockchain.expiration or 300)
        # ensure at least 5 minutes to avoid expiration race with head block time drift
        exp_seconds = max(exp_seconds, 300)
        if self.blockchain.is_connected():
            dgp = self.blockchain.get_dynamic_global_properties(use_stored_data=False)
            head_time_str = dgp.get("time")
            from datetime import datetime, timedelta, timezone

            head_time = datetime.strptime(head_time_str, "%Y-%m-%dT%H:%M:%S").replace(
                tzinfo=timezone.utc
            )
            now_utc = datetime.now(timezone.utc)
            base_time = max(head_time, now_utc)
            expiration_dt = base_time + timedelta(seconds=exp_seconds)
            expiration = expiration_dt.strftime("%Y-%m-%dT%H:%M:%S")
        else:
            expiration = formatTimeFromNow(exp_seconds)

        # We now wrap everything into an actual transaction
        if ref_block_num is None or ref_block_prefix is None:
            ref_block_num, ref_block_prefix = self.get_block_params(use_head_block=True)
        if self._use_ledger:
            self.ledgertx = Ledger_Transaction(
                ref_block_prefix=ref_block_prefix,
                expiration=expiration,
                operations=ops,
                ref_block_num=ref_block_num,
                custom_chains=self.blockchain.custom_chains,
                prefix=self.blockchain.prefix,
            )

        self.tx = Signed_Transaction(
            ref_block_prefix=ref_block_prefix,
            expiration=expiration,
            operations=ops,
            ref_block_num=ref_block_num,
            custom_chains=self.blockchain.custom_chains,
            prefix=self.blockchain.prefix,
        )

        super().update(self.tx.json())
        self._unset_require_reconstruction()

    def get_block_params(self, use_head_block=False):
        """Auxiliary method to obtain ``ref_block_num`` and
        ``ref_block_prefix``. Requires a connection to a
        node!
        """

        dynBCParams = self.blockchain.get_dynamic_global_properties(use_stored_data=False)
        # fix for corner case where last_irreversible_block_num == head_block_number
        # then int(dynBCParams["last_irreversible_block_num"]) + 1 does not exists
        # and BlockHeader throws error
        if use_head_block or int(dynBCParams["last_irreversible_block_num"]) == int(
            dynBCParams["head_block_number"]
        ):
            ref_block_num = dynBCParams["head_block_number"] & 0xFFFF
            ref_block_prefix = struct.unpack_from("<I", unhexlify(dynBCParams["head_block_id"]), 4)[
                0
            ]
        else:
            # need to get subsequent block because block head doesn't return 'id' - stupid
            from .block import BlockHeader

            block = BlockHeader(
                int(dynBCParams["last_irreversible_block_num"]) + 1,
                blockchain_instance=self.blockchain,
            )
            ref_block_num = dynBCParams["last_irreversible_block_num"] & 0xFFFF
            ref_block_prefix = struct.unpack_from("<I", unhexlify(block["previous"]), 4)[0]
        return ref_block_num, ref_block_prefix

    def sign(self, reconstruct_tx=True):
        """
        Sign the built transaction using HiveSigner, a Ledger device, or local WIFs and attach signatures to the builder.

        If the transaction is not constructed (or if reconstruct_tx is True) the transaction will be reconstructed before signing. The method attempts signing in this order:
        1. Ledger (if ledger mode is active) — signs with the Ledger device and appends signatures.
        2. Local WIFs from the builder — uses stored WIFs to sign the transaction and appends signatures.

        Parameters:
            reconstruct_tx (bool): If False and the transaction is already constructed, existing signatures are preserved and the transaction will not be rebuilt before signing. Defaults to True.

        Returns:
            The object returned by the signing step:
              - Ledger_Transaction when signed via Ledger,
              - Signed_Transaction when signed locally with WIFs.
            Returns None if there are no operations to sign.

        Raises:
            MissingKeyError: If local signing is attempted but no WIFs are available.
        """
        if not self._is_constructed() or (self._is_constructed() and reconstruct_tx):
            self.constructTx()
        if "operations" not in self or not self["operations"]:
            return
        # We need to set the default prefix, otherwise pubkeys are
        # presented wrongly!
        if self.blockchain.rpc is not None:
            operations.default_prefix = self.blockchain.chain_params["prefix"]
        elif "blockchain" in self:
            operations.default_prefix = self["blockchain"]["prefix"]

        if self._use_ledger:
            # try:
            #    ledgertx = Ledger_Transaction(**self.json(with_prefix=True))
            #    ledgertx.add_custom_chains(self.blockchain.custom_chains)
            # except Exception:
            #    raise ValueError("Invalid TransactionBuilder Format")
            # ledgertx.sign(self.path, chain=self.blockchain.chain_params)
            self.ledgertx.sign(self.path, chain=self.blockchain.chain_params)
            self["signatures"].extend(self.ledgertx.json().get("signatures"))
            return self.ledgertx
        else:
            if not any(self.wifs):
                raise MissingKeyError

            self.tx.sign(list(self.wifs), chain=self.blockchain.chain_params)
            # Defensive: ensure self["signatures"] is a list before extend
            if isinstance(self["signatures"], str):
                log.warning(
                    "self['signatures'] was a string, converting to list to avoid AttributeError."
                )
                self["signatures"] = [self["signatures"]]
            sigs = self.tx.json().get("signatures")
            if isinstance(sigs, str):
                sigs = [sigs]
            self["signatures"].extend(sigs)
            return self.tx

    def verify_authority(self):
        """Verify the authority of the signed transaction"""
        try:
            self.blockchain.rpc.set_next_node_on_empty_reply(False)
            args = {"trx": self.json()}
            ret = self.blockchain.rpc.verify_authority(args, api="database_api")
            if not ret:
                raise InsufficientAuthorityError
            elif isinstance(ret, dict) and "valid" in ret and not ret["valid"]:
                raise InsufficientAuthorityError
        except Exception as e:
            raise e

    def get_potential_signatures(self):
        """Returns public key from signature"""
        if not self.blockchain.is_connected():
            raise OfflineHasNoRPCException("No RPC available in offline mode!")
        self.blockchain.rpc.set_next_node_on_empty_reply(False)
        args = {"trx": self.json()}
        ret = self.blockchain.rpc.get_potential_signatures(args, api="database_api")
        if "keys" in ret:
            ret = ret["keys"]
        return ret

    def get_transaction_hex(self):
        """Returns a hex value of the transaction"""
        if not self.blockchain.is_connected():
            raise OfflineHasNoRPCException("No RPC available in offline mode!")
        self.blockchain.rpc.set_next_node_on_empty_reply(False)
        args = {"trx": self.json()}
        ret = self.blockchain.rpc.get_transaction_hex(args, api="database_api")
        if "hex" in ret:
            ret = ret["hex"]
        return ret

    def get_required_signatures(self, available_keys=list()):
        """
        Return the subset of public keys required to sign this transaction from a set of available keys.

        This method requires an active RPC connection and delegates to the node's
        get_required_signatures API to determine which of the provided available_keys
        are necessary to satisfy the transaction's authority requirements.

        Parameters:
            available_keys (list): Iterable of public key strings to consider when
                determining required signers.

        Returns:
            list: Public key strings that the node reports are required to sign the transaction.

        Raises:
            OfflineHasNoRPCException: If called while offline (no RPC available).
        """
        if not self.blockchain.is_connected():
            raise OfflineHasNoRPCException("No RPC available in offline mode!")
        self.blockchain.rpc.set_next_node_on_empty_reply(False)
        args = {"trx": self.json(), "available_keys": available_keys}
        ret = self.blockchain.rpc.get_required_signatures(args, api="database_api")
        return ret

    def broadcast(self, max_block_age=-1, trx_id=True):
        """
        Broadcast the built transaction to the Hive network and clear the builder state.

        If the transaction is not yet signed this method will attempt to sign it first.
        If no operations are present the call returns None. When broadcasting is disabled
        (nobroadcast) the constructed transaction dict is returned and the builder is cleared.

        Parameters:
            max_block_age (int): Passed to appbase/network_broadcast calls to constrain
                acceptable block age; ignored for condenser API paths. Default -1.
            trx_id (bool): If True and a signing step produced a transaction id, attach
                it to the returned result when the RPC response lacks a `trx_id`. Default True.

        Returns:
            dict or whatever the underlying broadcast method returns, or None if there
            are no operations to broadcast.

        Side effects:
            - Clears internal transaction state on successful broadcast or on errors.
            - May raise exceptions from the signing or RPC broadcast calls.
        """
        # Cannot broadcast an empty transaction
        if not self._is_signed():
            sign_ret = self.sign()
        else:
            sign_ret = None

        if "operations" not in self or not self["operations"]:
            return
        ret = self.json()

        if not self._use_condenser_api:
            args = {"trx": self.json(), "max_block_age": -1}
            broadcast_api = "network_broadcast_api"
        else:
            args = self.json()
            broadcast_api = "condenser_api"

        if self.blockchain.nobroadcast:
            log.info("Not broadcasting anything!")
            self.clear()
            return ret
        # Broadcast
        try:
            self.blockchain.rpc.set_next_node_on_empty_reply(False)
            if self.blockchain.blocking and self._use_condenser_api:
                ret = self.blockchain.rpc.broadcast_transaction_synchronous(args, api=broadcast_api)
                if "trx" in ret:
                    ret.update(**ret.get("trx"))
            else:
                self.blockchain.rpc.broadcast_transaction(args, api=broadcast_api)
        except Exception as e:
            # log.error("Could Not broadcasting anything!")
            self.clear()
            raise e
        if sign_ret is not None and "trx_id" not in ret and trx_id:
            ret["trx_id"] = sign_ret.id
        self.clear()
        return ret

    def clear(self):
        """Clear the transaction builder and start from scratch"""
        self.ops = []
        self.wifs = set()
        self.signing_accounts = []
        self.ref_block_num = None
        self.ref_block_prefix = None
        # This makes sure that _is_constructed will return False afterwards
        self["expiration"] = None
        super().__init__({})

    def addSigningInformation(self, account, permission, reconstruct_tx=False):
        """This is a private method that adds side information to a
        unsigned/partial transaction in order to simplify later
        signing (e.g. for multisig or coldstorage)

        Not needed when "appendWif" was already or is going to be used

        FIXME: Does not work with owner keys!

        :param bool reconstruct_tx: when set to False and tx
            is already contructed, it will not reconstructed
            and already added signatures remain

        """
        if not self._is_constructed() or (self._is_constructed() and reconstruct_tx):
            self.constructTx()
        self["blockchain"] = self.blockchain.chain_params

        if isinstance(account, PublicKey):
            self["missing_signatures"] = [str(account)]
        else:
            accountObj = Account(account, blockchain_instance=self.blockchain)
            authority = accountObj[permission]
            # We add a required_authorities to be able to identify
            # how to sign later. This is an array, because we
            # may later want to allow multiple operations per tx
            self.update({"required_authorities": {accountObj["name"]: authority}})
            for account_auth in authority["account_auths"]:
                account_auth_account = Account(account_auth[0], blockchain_instance=self.blockchain)
                self["required_authorities"].update(
                    {account_auth[0]: account_auth_account.get(permission)}
                )

            # Try to resolve required signatures for offline signing
            self["missing_signatures"] = [x[0] for x in authority["key_auths"]]
            # Add one recursion of keys from account_auths:
            for account_auth in authority["account_auths"]:
                account_auth_account = Account(account_auth[0], blockchain_instance=self.blockchain)
                self["missing_signatures"].extend(
                    [x[0] for x in account_auth_account[permission]["key_auths"]]
                )

    def appendMissingSignatures(self):
        """Store which accounts/keys are supposed to sign the transaction

        This method is used for an offline-signer!
        """
        missing_signatures = self.get("missing_signatures", [])
        for pub in missing_signatures:
            try:
                wif = self.blockchain.wallet.getPrivateKeyForPublicKey(pub)
                if wif:
                    self.appendWif(wif)
            except MissingKeyError:
                wif = None
