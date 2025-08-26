from __future__ import absolute_import, division, print_function, unicode_literals

import logging

from nectar import Hive as Steem
from nectar.account import Account

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


if __name__ == "__main__":
    # Example testnet endpoints removed; use a Hive API endpoint instead
    stm = Steem(node="https://api.hive.blog")
    stm.wallet.unlock(pwd="pwd123")

    account = Account("thecrazygm", steem_instance=stm)
    print(account.get_voting_power())

    account.transfer("thecrazygm", 0.001, "HBD", "test")
