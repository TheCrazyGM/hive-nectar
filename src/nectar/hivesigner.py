# -*- coding: utf-8 -*-
import json

try:
    from urllib.parse import urlencode, urljoin
except ImportError:
    from urllib import urlencode

    from urlparse import urljoin
import logging

import requests
from six import PY2

from nectar.amount import Amount
from nectar.exceptions import MissingKeyError, WalletExists
from nectar.instance import shared_blockchain_instance
from nectarstorage.exceptions import KeyAlreadyInStoreException

log = logging.getLogger(__name__)


class HiveSigner(object):
    """HiveSigner

    :param str scope: comma separated string with scopes
        login,offline,vote,comment,delete_comment,comment_options,custom_json,claim_reward_balance


    .. code-block:: python

        # Run the login_app in examples and login with an account
        from nectar import Hive
        from nectar.hivesigner import HiveSigner
        from nectar.comment import Comment
        hs = HiveSigner(client_id="nectarflower")
        hive = Hive(HiveSigner=hs)
        hive.wallet.unlock("supersecret-passphrase")
        post = Comment("author/permlink", blockchain_instance=hive)
        post.upvote(voter="test")  # replace "test" with your account

    Examples for creating HiveSigner urls for broadcasting in browser:

    .. testoutput::

        from nectar import Hive
        from nectar.account import Account
        from nectar.hivesigner import HiveSigner
        from pprint import pprint
        hive = Hive(nobroadcast=True, unsigned=True)
        hs = HiveSigner(blockchain_instance=hive)
        acc = Account("test", blockchain_instance=hive)
        pprint(hs.url_from_tx(acc.transfer("test1", 1, "HIVE", "test")))

    .. testcode::

        'https://hivesigner.com/sign/transfer?from=test&to=test1&amount=1.000+HIVE&memo=test'

    .. testoutput::

        from nectar import Hive
        from nectar.transactionbuilder import TransactionBuilder
        from nectarbase import operations
        from nectar.hivesigner import HiveSigner
        from pprint import pprint
        hive = Hive(nobroadcast=True, unsigned=True)
        hs = HiveSigner(blockchain_instance=hive)
        tx = TransactionBuilder(blockchain_instance=hive)
        op = operations.Transfer(**{"from": 'test',
                                    "to": 'test1',
                                    "amount": '1.000 HIVE',
                                    "memo": 'test'})
        tx.appendOps(op)
        pprint(hs.url_from_tx(tx.json()))

    .. testcode::

        'https://hivesigner.com/sign/transfer?from=test&to=test1&amount=1.000+HIVE&memo=test'

    """

    def __init__(self, blockchain_instance=None, *args, **kwargs):
        """
        Initialize HiveSigner integration.

        Sets up the blockchain client (uses provided instance or the shared global), OAuth/client configuration, and the token store.

        Detailed behavior:
        - Resolves self.blockchain from blockchain_instance or shared_blockchain_instance().
        - Reads defaults from blockchain config for client_id, scope, OAuth base URL, API URL, and hot-sign redirect URI.
        - Normalizes hot_sign_redirect_uri to None if an empty string is provided.
        - Stores get_refresh_token, client_id, scope, hs_oauth_base_url, and hs_api_url on the instance.
        - Token handling:
          - If a non-empty "token" is provided in kwargs, an in-memory token store is created, the access token is set, the associated username is fetched via me(), and the token is stored under that username.
          - Otherwise a persistent token store is used: either the token_store passed in kwargs or a SqliteEncryptedTokenStore initialized with the blockchain config and kwargs.
        """
        self.blockchain = blockchain_instance or shared_blockchain_instance()
        self.access_token = None
        config = self.blockchain.config
        self.get_refresh_token = kwargs.get("get_refresh_token", False)
        self.hot_sign_redirect_uri = kwargs.get(
            "hot_sign_redirect_uri", config["hot_sign_redirect_uri"]
        )
        if self.hot_sign_redirect_uri == "":
            self.hot_sign_redirect_uri = None
        self.client_id = kwargs.get("client_id", config["hs_client_id"])
        self.scope = kwargs.get("scope", "login")
        self.hs_oauth_base_url = kwargs.get("hs_oauth_base_url", config["hs_oauth_base_url"])
        self.hs_api_url = kwargs.get("hs_api_url", config["hs_api_url"])

        if "token" in kwargs and len(kwargs["token"]) > 0:
            from nectarstorage import InRamPlainTokenStore

            self.store = InRamPlainTokenStore()
            token = kwargs["token"]
            self.set_access_token(token)
            name = self.me()["user"]
            self.setToken({name: token})
        else:
            """ If no keys are provided manually we load the SQLite
                keyStorage
            """
            from nectarstorage import SqliteEncryptedTokenStore

            self.store = kwargs.get(
                "token_store",
                SqliteEncryptedTokenStore(config=config, **kwargs),
            )

    @property
    def headers(self):
        """
        Return the HTTP Authorization headers for the current access token.

        Returns:
            dict: A headers dictionary with the "Authorization" key set to the current access token (may be None if no token is set).
        """
        return {"Authorization": self.access_token}

    def setToken(self, loadtoken):
        """
        Force-add tokens into the token store from an in-memory mapping.

        Accepts a mapping of public-name -> token and stores each entry into the configured token store. Intended for use when tokens are provided directly (e.g., via a `token` argument) and should be loaded into the in-memory store.

        Parameters:
            loadtoken (dict): Mapping where keys are public names and values are the corresponding private token strings.

        Raises:
            ValueError: If `loadtoken` is not a dict.
        """
        log.debug("Force setting of private token. Not using the wallet database!")
        if not isinstance(loadtoken, (dict)):
            raise ValueError("token must be a dict variable!")
        for name in loadtoken:
            self.store.add(loadtoken[name], name)

    def is_encrypted(self):
        """Is the key store encrypted?"""
        return self.store.is_encrypted()

    def unlock(self, pwd):
        """Unlock the wallet database"""
        unlock_ok = None
        if self.store.is_encrypted():
            unlock_ok = self.store.unlock(pwd)
        return unlock_ok

    def lock(self):
        """Lock the wallet database"""
        lock_ok = False
        if self.store.is_encrypted():
            lock_ok = self.store.lock()
        return lock_ok

    def unlocked(self):
        """Is the wallet database unlocked?"""
        unlocked = True
        if self.store.is_encrypted():
            unlocked = not self.store.locked()
        return unlocked

    def locked(self):
        """Is the wallet database locked?"""
        if self.store.is_encrypted():
            return self.store.locked()
        else:
            return False

    def changePassphrase(self, new_pwd):
        """Change the passphrase for the wallet database"""
        self.store.change_password(new_pwd)

    def created(self):
        """Do we have a wallet database already?"""
        if len(self.store.getPublicKeys()):
            # Already keys installed
            return True
        else:
            return False

    def create(self, pwd):
        """Alias for :func:`newWallet`

        :param str pwd: Passphrase for the created wallet
        """
        self.newWallet(pwd)

    def newWallet(self, pwd):
        """Create a new wallet database

        :param str pwd: Passphrase for the created wallet
        """
        if self.created():
            raise WalletExists("You already have created a wallet!")
        self.store.unlock(pwd)

    def addToken(self, name, token):
        if str(name) in self.store:
            raise KeyAlreadyInStoreException("Token already in the store")
        self.store.add(str(token), str(name))

    def getTokenForAccountName(self, name):
        """Obtain the private token for a given public name

        :param str name: Public name
        """
        if str(name) not in self.store:
            raise MissingKeyError
        return self.store.getPrivateKeyForPublicKey(str(name))

    def removeTokenFromPublicName(self, name):
        """Remove a token from the wallet database

        :param str name: token to be removed
        """
        self.store.delete(str(name))

    def getPublicNames(self):
        """Return all installed public token"""
        if self.store is None:
            return
        return self.store.getPublicNames()

    def get_login_url(self, redirect_uri, **kwargs):
        """Returns a login url for receiving token from HiveSigner"""
        client_id = kwargs.get("client_id", self.client_id)
        scope = kwargs.get("scope", self.scope)
        get_refresh_token = kwargs.get("get_refresh_token", self.get_refresh_token)
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
        }
        if get_refresh_token:
            params.update(
                {
                    "response_type": "code",
                }
            )
        if PY2:
            return urljoin(
                self.hs_oauth_base_url, "authorize?" + urlencode(params).replace("%2C", ",")
            )
        else:
            return urljoin(self.hs_oauth_base_url, "authorize?" + urlencode(params, safe=","))

    def get_access_token(self, code):
        post_data = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.getTokenForAccountName(self.client_id),
        }

        r = requests.post(urljoin(self.hs_api_url, "oauth2/token/"), data=post_data)

        return r.json()

    def me(self, username=None):
        """
        Retrieve the current user's information from HiveSigner.

        If a username is provided, sets the access token for that username (via set_username) before calling the HiveSigner "me" endpoint. Performs an authenticated POST to the HiveSigner me endpoint and returns the parsed JSON response.

        Parameters:
            username (str, optional): Public account name whose token should be used for the request. If omitted, the currently configured access token is used.

        Returns:
            dict: Parsed JSON response from the HiveSigner me endpoint.
        """
        if username:
            self.set_username(username)
        url = urljoin(self.hs_api_url, "me/")
        r = requests.post(url, headers=self.headers)
        return r.json()

    def set_access_token(self, access_token):
        """Is needed for :func:`broadcast` and :func:`me`"""
        self.access_token = access_token

    def set_username(self, username, permission="posting"):
        """Set a username for the next :func:`broadcast` or :func:`me` operation.
        The necessary token is fetched from the wallet
        """
        if permission != "posting":
            self.access_token = None
            return
        self.access_token = self.getTokenForAccountName(username)

    def broadcast(self, operations, username=None):
        """
        Broadcast a list of Hive operations via the HiveSigner API.

        Sends a POST request to the HiveSigner broadcast endpoint with the provided operations. If `username` is given, the method will set the access token for that user before sending the request.

        Parameters:
            operations (list): A list of operations in the form [[operation_name, operation_payload], ...].
            username (str, optional): Public account name whose stored token should be used for authorization.

        Returns:
            dict or bytes: The parsed JSON response from the API, or raw response content if the body is not valid JSON.
        """
        url = urljoin(self.hs_api_url, "broadcast/")
        data = {
            "operations": operations,
        }
        if username:
            self.set_username(username)
        headers = self.headers.copy()
        headers.update(
            {
                "Content-Type": "application/json; charset=utf-8",
                "Accept": "application/json",
            }
        )

        r = requests.post(url, headers=headers, data=json.dumps(data))
        try:
            return r.json()
        except ValueError:
            return r.content

    def refresh_access_token(self, code, scope):
        post_data = {
            "grant_type": "refresh_token",
            "refresh_token": code,
            "client_id": self.client_id,
            "client_secret": self.getTokenForAccountName(self.client_id),
            "scope": scope,
        }

        r = requests.post(
            urljoin(self.hs_api_url, "oauth2/token/"),
            data=post_data,
        )

        return r.json()

    def revoke_token(self, access_token):
        post_data = {
            "access_token": access_token,
        }

        r = requests.post(urljoin(self.hs_api_url, "oauth2/token/revoke"), data=post_data)

        return r.json()

    def update_user_metadata(self, metadata):
        put_data = {
            "user_metadata": metadata,
        }
        r = requests.put(urljoin(self.hs_api_url, "me/"), data=put_data, headers=self.headers)

        return r.json()

    def url_from_tx(self, tx, redirect_uri=None):
        """
        Generate HiveSigner hot-sign URLs for each operation in a transaction.

        Given a transaction dict (or an object with a .json() method returning such a dict), produce a HiveSigner "hot sign" URL for each operation. If the transaction has no operations an empty string is returned. For each operation the function normalizes parameter values before building the URL:
        - 3-element lists are treated as amounts and converted to the blockchain's Amount string when possible.
        - booleans are converted to 1 (True) or 0 (False).
        - other values are left as-is.

        Returns either a single URL string when the transaction contains one operation, a list of URL strings for multiple operations, or an empty string when there are no operations.

        Parameters:
            tx (dict | object): Transaction data or an object implementing .json() that returns a dict with an "operations" list.
            redirect_uri (str, optional): If provided, included in each generated hot-sign URL as the post-sign redirect target.
        """
        if not isinstance(tx, dict):
            tx = tx.json()
        if "operations" not in tx or not tx["operations"]:
            return ""
        urls = []
        operations = tx["operations"]
        for op in operations:
            operation = op[0]
            params = op[1]
            for key in params:
                value = params[key]
                if isinstance(value, list) and len(value) == 3:
                    try:
                        amount = Amount(value, blockchain_instance=self.blockchain)
                        params[key] = str(amount)
                    except Exception:
                        amount = None
                elif isinstance(value, bool):
                    if value:
                        params[key] = 1
                    else:
                        params[key] = 0
            urls.append(self.create_hot_sign_url(operation, params, redirect_uri=redirect_uri))
        if len(urls) == 1:
            return urls[0]
        else:
            return urls

    def sign(self, tx):
        """
        Create a transaction shaped as if signed by HiveSigner.

        This method does not perform real cryptographic signing locally; instead it validates
        the transaction structure and returns a copy containing a mock signature entry so
        callers that expect a "signed" transaction can proceed (actual signing is performed
        server-side by HiveSigner during broadcasting).

        Parameters:
            tx (dict): Transaction object that must include a non-empty "operations" list.

        Returns:
            dict: A copy of `tx` with a "signatures" list containing a mock HiveSigner signature.

        Raises:
            ValueError: If `tx` is not a dict or if it lacks a non-empty "operations" list.
        """
        if not isinstance(tx, dict):
            raise ValueError("Transaction must be a dictionary")

        if "operations" not in tx or not tx["operations"]:
            raise ValueError("Transaction must contain operations")

        # For HiveSigner, we don't actually sign locally - the signing happens
        # server-side when broadcast() is called. However, we need to return
        # a transaction that looks signed for compatibility.

        # Create a copy of the transaction
        signed_tx = tx.copy()

        # Add a mock signature to indicate this was processed by HiveSigner
        # In a real implementation, this would be replaced with actual signatures
        # from the HiveSigner API response
        mock_signature = "hivesigner_signature_placeholder"
        signed_tx["signatures"] = [mock_signature]

        log.debug(f"HiveSigner sign: processed transaction with {len(tx['operations'])} operations")
        return signed_tx
