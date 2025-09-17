from __future__ import absolute_import, division, print_function, unicode_literals

import logging
from datetime import timedelta
from timeit import default_timer as timer

from prettytable import PrettyTable

from nectar.account import Account
from nectar.block import Block
from nectar.blockchain import Blockchain
from nectar.comment import Comment
from nectar.hive import Hive
from nectar.nodelist import NodeList
from nectar.utils import (
    construct_authorperm,
    parse_time,
    resolve_authorpermvoter,
)
from nectar.vote import Vote
from nectarapi.exceptions import NumRetriesReached

FUTURES_MODULE = None
if not FUTURES_MODULE:
    try:
        from concurrent.futures import ThreadPoolExecutor, as_completed

        FUTURES_MODULE = "futures"
    except ImportError:
        FUTURES_MODULE = None
log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
quit_thread = False


def benchmark_node(node, how_many_minutes=10, how_many_seconds=30):
    """
    Benchmark a single Hive node by measuring block processing, account history retrieval, and basic RPC access latencies.

    Performs three timed phases against the provided node:
    1. Iterates historical blocks starting from a fixed block ID until a time limit (how_many_minutes) or per-call time limit (how_many_seconds) is reached, counting blocks and transactions.
    2. Iterates the account history of the fixed account "gtg" in reverse (batch_size=100) until the per-call time limit is reached, counting history entries.
    3. Measures the average latency of four representative operations (Vote, Comment, Account construction, and fetching followers) to produce an access-time metric.

    Parameters:
        node (str): URL or identifier of the Hive node to benchmark.
        how_many_minutes (int): Maximum span (in minutes) of blockchain history to walk from the starting block (default: 10).
        how_many_seconds (int): Per-phase timeout in seconds to abort a long-running loop/scan (default: 30).

    Returns:
        dict: A summary with the following keys:
            - successful (bool): False if a retriable error occurred during history or access phases.
            - node (str): The node value passed in.
            - error (str|None): Error message when a phase failed, otherwise None.
            - total_duration (float): Total elapsed seconds for the entire benchmark run.
            - block_count (int): Number of blocks processed (or -1 on error).
            - history_count (int): Number of account history entries processed (or -1 on error).
            - access_time (float): Average latency (seconds) of the measured RPC operations (or -1 on error).
            - follow_time (float): Measured time (seconds) for fetching followers in the access phase.
            - version (str): Blockchain version string reported by the node.
    """
    block_count = 0
    history_count = 0
    access_time = 0
    follow_time = 0
    blockchain_version = "0.0.0"
    successful = True
    error_msg = None
    start_total = timer()
    max_batch_size = None
    threading = False
    thread_num = 16

    authorpermvoter = "@gtg/hive-pressure-4-need-for-speed|gandalf"
    [author, permlink, voter] = resolve_authorpermvoter(authorpermvoter)
    authorperm = construct_authorperm(author, permlink)
    last_block_id = 19273700
    try:
        hv = Hive(node=node, num_retries=3, num_retries_call=3, timeout=30)
        blockchain = Blockchain(blockchain_instance=hv)
        blockchain_version = hv.get_blockchain_version()

        last_block = Block(last_block_id, blockchain_instance=hv)

        stopTime = last_block.time() + timedelta(seconds=how_many_minutes * 60)
        total_transaction = 0

        start = timer()
        for entry in blockchain.blocks(
            start=last_block_id,
            max_batch_size=max_batch_size,
            threading=threading,
            thread_num=thread_num,
        ):
            block_no = entry.identifier
            block_count += 1
            if "block" in entry:
                trxs = entry["block"]["transactions"]
            else:
                trxs = entry["transactions"]

            for tx in trxs:
                for op in tx["operations"]:
                    total_transaction += 1
            if "block" in entry:
                block_time = parse_time(entry["block"]["timestamp"])
            else:
                block_time = parse_time(entry["timestamp"])

            if block_time > stopTime:
                last_block_id = block_no
                break
            if timer() - start > how_many_seconds or quit_thread:
                break
    except NumRetriesReached:
        error_msg = "NumRetriesReached"
        block_count = -1
    except KeyboardInterrupt:
        error_msg = "KeyboardInterrupt"
        # quit = True
    except Exception as e:
        error_msg = str(e)
        block_count = -1

    try:
        hv = Hive(node=node, num_retries=3, num_retries_call=3, timeout=30)
        account = Account("gtg", blockchain_instance=hv)
        blockchain_version = hv.get_blockchain_version()

        start = timer()
        for acc_op in account.history_reverse(batch_size=100):
            history_count += 1
            if timer() - start > how_many_seconds or quit_thread:
                break
    except NumRetriesReached:
        error_msg = "NumRetriesReached"
        history_count = -1
        successful = False
    except KeyboardInterrupt:
        error_msg = "KeyboardInterrupt"
        history_count = -1
        successful = False
        # quit = True
    except Exception as e:
        error_msg = str(e)
        history_count = -1
        successful = False

    try:
        hv = Hive(node=node, num_retries=3, num_retries_call=3, timeout=30)
        account = Account("gtg", blockchain_instance=hv)
        blockchain_version = hv.get_blockchain_version()

        start = timer()
        Vote(authorpermvoter, blockchain_instance=hv)
        stop = timer()
        vote_time = stop - start
        start = timer()
        Comment(authorperm, blockchain_instance=hv)
        stop = timer()
        comment_time = stop - start
        start = timer()
        Account(author, blockchain_instance=hv)
        stop = timer()
        account_time = stop - start
        start = timer()
        account.get_followers()
        stop = timer()
        follow_time = stop - start
        access_time = (vote_time + comment_time + account_time + follow_time) / 4.0
    except NumRetriesReached:
        error_msg = "NumRetriesReached"
        access_time = -1
    except KeyboardInterrupt:
        error_msg = "KeyboardInterrupt"
        # quit = True
    except Exception as e:
        error_msg = str(e)
        access_time = -1
    return {
        "successful": successful,
        "node": node,
        "error": error_msg,
        "total_duration": timer() - start_total,
        "block_count": block_count,
        "history_count": history_count,
        "access_time": access_time,
        "follow_time": follow_time,
        "version": blockchain_version,
    }


if __name__ == "__main__":
    how_many_seconds = 30
    how_many_minutes = 10
    threading = True
    set_default_nodes = False
    quit_thread = False
    benchmark_time = timer()

    nodelist = NodeList()
    nodes = nodelist.get_nodes(normal=True, appbase=True, dev=True)
    t = PrettyTable(["node", "N blocks", "N acc hist", "dur. call in s"])
    t.align = "l"
    t2 = PrettyTable(["node", "version"])
    t2.align = "l"
    working_nodes = []
    results = []
    if threading and FUTURES_MODULE:
        pool = ThreadPoolExecutor(max_workers=len(nodes) + 1)
        futures = []
        for node in nodes:
            futures.append(pool.submit(benchmark_node, node, how_many_minutes, how_many_seconds))
        try:
            results = [r.result() for r in as_completed(futures)]
        except KeyboardInterrupt:
            quit_thread = True
            print("benchmark aborted.")
    else:
        for node in nodes:
            print("Current node:", node)
            result = benchmark_node(node, how_many_minutes, how_many_seconds)
            results.append(result)
    for result in results:
        t2.add_row([result["node"], result["version"]])
    print(t2)
    print("\n")

    sortedList = sorted(results, key=lambda self: self["history_count"], reverse=True)
    for result in sortedList:
        if result["successful"]:
            t.add_row(
                [
                    result["node"],
                    result["block_count"],
                    result["history_count"],
                    ("%.2f" % (result["access_time"])),
                ]
            )
            working_nodes.append(result["node"])
    print(t)
    print("\n")
    print("Total benchmark time: %.2f s\n" % (timer() - benchmark_time))
    if set_default_nodes:
        hv = Hive(offline=True)
        hv.set_default_nodes(working_nodes)
    else:
        print("hive-nectar set nodes " + str(working_nodes))
