from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import time
from datetime import datetime, timedelta

from nectar.block import Block
from nectar.blockchain import Blockchain
from nectar.hive import Hive
from nectar.nodelist import NodeList
from nectar.utils import formatTimedelta

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


if __name__ == "__main__":
    node_setup = 1
    how_many_hours = 1
    nodes = NodeList()
    if node_setup == 0:
        hv = Hive(node=nodes.get_nodes(normal=True, https=True), num_retries=10)
        max_batch_size = None
        threading = False
        thread_num = 8
    elif node_setup == 1:
        hv = Hive(node=nodes.get_nodes(normal=True, https=True), num_retries=10)
        max_batch_size = None
        threading = True
        thread_num = 16
    elif node_setup == 2:
        hv = Hive(node=nodes.get_nodes(appbase=False, https=True), num_retries=10)
        max_batch_size = None
        threading = True
        thread_num = 16
    blockchain = Blockchain(blockchain_instance=hv)
    last_block_id = 19273700
    last_block = Block(last_block_id, blockchain_instance=hv)
    startTime = datetime.now()

    stopTime = last_block.time() + timedelta(seconds=how_many_hours * 60 * 60)
    ltime = time.time()
    cnt = 0
    total_transaction = 0

    start_time = time.time()
    last_node = hv.rpc.url
    print("Current node:", last_node)
    for entry in blockchain.blocks(
        start=last_block_id,
        max_batch_size=max_batch_size,
        threading=threading,
        thread_num=thread_num,
        thread_limit=1200,
    ):
        block_no = entry.identifier
        if "block" in entry:
            trxs = entry["block"]["transactions"]
        else:
            trxs = entry["transactions"]

        for tx in trxs:
            for op in tx["operations"]:
                total_transaction += 1
        if "block" in entry:
            block_time = entry["block"]["timestamp"]
        else:
            block_time = entry["timestamp"]

        if block_time > stopTime:
            total_duration = formatTimedelta(datetime.now() - startTime)
            last_block_id = block_no
            avtran = total_transaction / (last_block_id - 19273700)
            print(
                "* HOUR mark: Processed %d blockchain hours in %s"
                % (how_many_hours, total_duration)
            )
            print(
                "* Blocks %d, Transactions %d (Avg. per Block %f)"
                % ((last_block_id - 19273700), total_transaction, avtran)
            )
            break

        if block_no != last_block_id:
            cnt += 1
            last_block_id = block_no
            if last_block_id % 100 == 0:
                now = time.time()
                duration = now - ltime
                total_duration = now - start_time
                speed = int(100000.0 / duration) * 1.0 / 1000
                avspeed = int((last_block_id - 19273700) * 1000 / total_duration) * 1.0 / 1000
                avtran = total_transaction / (last_block_id - 19273700)
                ltime = now
                if last_node != hv.rpc.url:
                    last_node = hv.rpc.url
                    print("Current node:", last_node)
                print(
                    "* 100 blocks processed in %.2f seconds. Speed %.2f. Avg: %.2f. Avg.Trans:"
                    "%.2f Count: %d Block minutes: %d"
                    % (duration, speed, avspeed, avtran, cnt, cnt * 3 / 60)
                )
