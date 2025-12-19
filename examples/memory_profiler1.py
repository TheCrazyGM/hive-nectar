import logging
from datetime import datetime

from memory_profiler import profile

from nectar import Hive as Hive
from nectar.account import Account
from nectar.blockchain import Blockchain
from nectar.instance import set_shared_blockchain_instance

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@profile
def profiling(name_list):
    """
    Profile memory while retrieving account histories and recent blockchain blocks.

    Creates a Hive instance and registers it as the shared blockchain instance, then iterates over each account name in name_list to:
    - print the account name,
    - instantiate an Account and print its virtual operation count,
    - scan the account history in reverse up to 2018-04-22 00:00:00 and print the last history element found.

    After processing accounts, it constructs a Blockchain instance, determines the current block number, streams the last 20 blocks (current_num-20..current_num), prints each block number as it is streamed, and prints the last block element seen.

    Parameters:
        name_list (iterable[str]): Iterable of account name strings to process.

    Side effects:
        - Registers a shared blockchain instance via set_shared_blockchain_instance(hv).
        - Prints progress and results to standard output.

    Returns:
        None
    """
    hv = Hive()
    set_shared_blockchain_instance(hv)
    del hv
    print("start")
    for name in name_list:
        print("account: %s" % (name))
        acc = Account(name)
        max_index = acc.virtual_op_count()
        print(max_index)
        stopTime = datetime(2018, 4, 22, 0, 0, 0)
        hist_elem = None
        for h in acc.history_reverse(stop=stopTime):
            hist_elem = h
        print(hist_elem)
    print("blockchain")
    blockchain_object = Blockchain()
    current_num = blockchain_object.get_current_block_num()
    startBlockNumber = current_num - 20
    endBlockNumber = current_num
    block_elem = None
    for o in blockchain_object.stream(start=startBlockNumber, stop=endBlockNumber):
        print("block %d" % (o["block_num"]))
        block_elem = o
    print(block_elem)


if __name__ == "__main__":
    account_list = [
        "utopian-io",
        "busy.org",
        "minnowsupport",
        "qurator",
        "thesteemengine",
        "ethandsmith",
        "make-a-whale",
        "feedyourminnows",
        "steembasicincome",
        "sbi2",
        "sbi3",
        "sbi4",
        "sbi5",
        "sbi6",
        "steemdunk",
        "thehumanbot",
        "resteemable",
        "kobusu",
        "mariachan",
        "qustodian",
        "randowhale",
        "bumper",
        "minnowbooster",
        "smartsteem",
        "steemlike",
        "parosai",
        "koinbot",
        "steemfunding",
    ]
    profiling(account_list)
