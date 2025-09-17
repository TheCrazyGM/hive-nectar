from __future__ import absolute_import, division, print_function, unicode_literals

import logging

from nectar import Hive as Hive
from nectar.account import Account
from nectar.block import Block
from nectar.blockchain import Blockchain
from nectargraphenebase.account import PasswordKey

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

password = "secretPassword"
username = "nectar5"
useWallet = False
walletpassword = "123"

if __name__ == "__main__":
    testnet_node = "https://testnet.steem.vc"
    hv = Hive(node=testnet_node)
    prefix = hv.prefix
    # curl --data "username=username&password=secretPassword" https://testnet.steem.vc/create
    if useWallet:
        hv.wallet.wipe(True)
        hv.wallet.create(walletpassword)
        hv.wallet.unlock(walletpassword)
    active_key = PasswordKey(username, password, role="active", prefix=prefix)
    owner_key = PasswordKey(username, password, role="owner", prefix=prefix)
    posting_key = PasswordKey(username, password, role="posting", prefix=prefix)
    memo_key = PasswordKey(username, password, role="memo", prefix=prefix)
    active_pubkey = active_key.get_public_key()
    owner_pubkey = owner_key.get_public_key()
    posting_pubkey = posting_key.get_public_key()
    memo_pubkey = memo_key.get_public_key()
    active_privkey = active_key.get_private_key()
    posting_privkey = posting_key.get_private_key()
    owner_privkey = owner_key.get_private_key()
    memo_privkey = memo_key.get_private_key()
    if useWallet:
        hv.wallet.addPrivateKey(owner_privkey)
        hv.wallet.addPrivateKey(active_privkey)
        hv.wallet.addPrivateKey(memo_privkey)
        hv.wallet.addPrivateKey(posting_privkey)
    else:
        hv = Hive(
            node=testnet_node,
            wif={
                "active": str(active_privkey),
                "posting": str(posting_privkey),
                "memo": str(memo_privkey),
            },
        )
    account = Account(username, blockchain_instance=hv)
    if account["name"] == "nectar":
        account.disallow("nectar1", permission="posting")
        account.allow("nectar1", weight=1, permission="posting", account=None)
        account.follow("nectar1")
    elif account["name"] == "nectar5":
        account.allow("nectar4", weight=2, permission="active", account=None)
    if useWallet:
        hv.wallet.getAccountFromPrivateKey(str(active_privkey))

    # hv.create_account("nectar1", creator=account, password=password1)

    account1 = Account("nectar1", blockchain_instance=hv)
    b = Blockchain(blockchain_instance=hv)
    blocknum = b.get_current_block().identifier

    account.transfer("nectar1", 1, "HBD", "test")
    b1 = Block(blocknum, blockchain_instance=hv)
