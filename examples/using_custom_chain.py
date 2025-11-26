import logging

from nectar import Hive as Hive

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


if __name__ == "__main__":
    hv = Hive(
        node=["https://api.hive.blog"],
        custom_chains={
            "TESTNETHF20": {
                "chain_assets": [
                    {"asset": "@@000000013", "symbol": "HBD", "precision": 3, "id": 0},
                    {"asset": "@@000000021", "symbol": "HIVE", "precision": 3, "id": 1},
                    {"asset": "@@000000037", "symbol": "VESTS", "precision": 6, "id": 2},
                ],
                "chain_id": "46d82ab7d8db682eb1959aed0ada039a6d49afa1602491f93dde9cac3e8e6c32",
                "min_version": "0.20.0",
                "prefix": "TST",
            }
        },
    )
    print(hv.get_blockchain_version())
    print(hv.get_config()["HIVE_CHAIN_ID"])
