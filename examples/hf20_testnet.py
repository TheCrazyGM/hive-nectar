import logging

from nectar import Hive as Hive
from nectar.account import Account

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


if __name__ == "__main__":
    # Example testnet endpoints removed; use a Hive API endpoint instead
    hv = Hive(node="https://api.hive.blog")
    hv.wallet.unlock(pwd="pwd123")

    account = Account("thecrazygm", blockchain_instance=hv)
    print(account.get_voting_power())

    account.transfer("thecrazygm", 0.001, "HBD", "test")
