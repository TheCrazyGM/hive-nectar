import argparse
import logging
import sys
from datetime import timedelta
from timeit import default_timer as timer

from prettytable import PrettyTable

from nectar import Hive
from nectar.block import Block
from nectar.blockchain import Blockchain
from nectar.nodelist import NodeList
from nectar.utils import parse_time

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def parse_args(args=None):
    """
    Parse command-line arguments for the script.

    One-line summary:
        Parse CLI arguments and return the parsed Namespace.

    Detailed:
        Accepts an optional list of argument strings (for testing). Parses a single optional
        positional argument "blockchain" which is a string specifying the blockchain to use;
        if omitted the parser will use standard input as the default value.

    Parameters:
        args (list[str] | None): Optional list of argument strings to parse. If None, uses
            arguments from the environment (sys.argv).

    Returns:
        argparse.Namespace: Parsed arguments with attribute `blockchain`.
    """
    d = "Show op type stats for hive."
    parser = argparse.ArgumentParser(description=d)
    parser.add_argument(
        "blockchain",
        type=str,
        nargs="?",
        default=sys.stdin,
        help="Blockchain (hive)",
    )
    return parser.parse_args(args)


def main(args=None):
    """
    Compute and print operation-type statistics for recent Hive blocks.

    Scans approximately one hour of recent Hive blocks (by default) and tallies operation types across all transactions found in that window. Results are printed as a table showing each operation type, its count, and its percentage of total operations.

    Parameters:
        args (list|None): Optional argument list in the same format as sys.argv[1:] or None to use command-line arguments parsed by argparse. Recognized options include a single optional positional "blockchain" identifier (defaults to Hive).
    """
    args = parse_args(args)
    blockchain = args.blockchain

    nodelist = NodeList()
    nodelist.update_nodes(weights={"block": 1})

    max_batch_size = 50
    threading = False
    thread_num = 16
    block_debug = 1000

    nodes = nodelist.get_hive_nodes()
    blk_inst = Hive(node=nodes, num_retries=3, num_retries_call=3, timeout=30)

    print(blk_inst)
    block_count = 0
    total_ops = 0
    total_trx = 0
    duration_s = 60 * 60 * 1
    blocksperday = int(duration_s / 3)

    blockchain = Blockchain(
        blockchain_instance=blk_inst,
    )
    current_block_num = blockchain.get_current_block_num()
    last_block_id = current_block_num - blocksperday

    last_block = Block(last_block_id, blockchain_instance=blk_inst)

    stopTime = last_block.time() + timedelta(seconds=duration_s)

    start = timer()
    op_stats = {}
    for entry in blockchain.blocks(
        start=last_block_id,
        max_batch_size=max_batch_size,
        threading=threading,
        thread_num=thread_num,
    ):
        if "block" in entry:
            block_time = parse_time(entry["block"]["timestamp"])
        else:
            block_time = entry["timestamp"]
        if block_time > stopTime:
            break
        block_count += 1
        if "block" in entry:
            trxs = entry["block"]["transactions"]
        else:
            trxs = entry["transactions"]
        for tx in trxs:
            total_trx += 1
            for op in tx["operations"]:
                if "_operation" in op["type"]:
                    op_type = op["type"][:-10]
                else:
                    op_type = op["type"]
                if op_type in op_stats:
                    op_stats[op_type] += 1
                else:
                    op_stats[op_type] = 1
                total_ops += 1

        ops_per_day = total_ops / block_count * blocksperday
        if block_count % (block_debug) == 0:
            print(
                "%d blocks remaining... estimated ops per day: %.1f"
                % (blocksperday - block_count, ops_per_day)
            )

    _duration = timer() - start
    t = PrettyTable(["Type", "Count", "percentage"])
    t.align = "l"
    op_list = []
    for o in op_stats:
        op_list.append({"type": o, "n": op_stats[o], "perc": op_stats[o] / total_ops * 100})
    op_list_sorted = sorted(op_list, key=lambda x: x["n"], reverse=True)
    for op in op_list_sorted:
        t.add_row([op["type"], op["n"], "%.2f %%" % op["perc"]])
    print(t)


if __name__ == "__main__":
    sys.exit(main())
