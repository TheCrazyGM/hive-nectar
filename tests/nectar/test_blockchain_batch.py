import unittest

from nectar import Hive
from nectar.blockchain import Blockchain
from nectar.instance import set_shared_blockchain_instance

from .nodes import get_hive_nodes

wif = "5KQwrPbwdL6PhXujxW37FSSQZ1JiwsST4cqQzDeyXtP79zkvFD3"


class Testcases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """
        Prepare class-level Hive test fixtures.

        Initializes a Hive client configured for testing (no broadcasting, retries, timeout, condenser disabled,
        and an active key), registers it as the shared blockchain instance, sets the default account to "test",
        and computes a short block range to use in tests (start = current_block - 20, stop = current_block).
        Also sets max_batch_size to 1 due to appbase batch-RPC limitations.

        Creates the following class attributes:
        - bts: configured Hive client instance
        - start (int): first block to include in test ranges
        - stop (int): last block to include in test ranges
        - max_batch_size (int): maximum batch size used when streaming (set to 1)
        """
        cls.bts = Hive(
            node=get_hive_nodes(),
            nobroadcast=True,
            num_retries=10,
            timeout=30,
            use_condenser=False,
            keys={"active": wif},
        )
        # from getpass import getpass
        # self.bts.wallet.unlock(getpass())
        set_shared_blockchain_instance(cls.bts)
        cls.bts.set_default_account("test")

        b = Blockchain(blockchain_instance=cls.bts)
        num = b.get_current_block_num()
        cls.start = num - 20
        cls.stop = num
        cls.max_batch_size = (
            1  # appbase does not support batch rpc calls at the momement (internal error)
        )

    def test_stream_batch(self):
        bts = self.bts
        b = Blockchain(blockchain_instance=bts)
        ops_stream = []
        opNames = ["transfer", "vote"]
        for op in b.stream(
            opNames=opNames,
            start=self.start,
            stop=self.stop,
            max_batch_size=self.max_batch_size,
            threading=False,
        ):
            ops_stream.append(op)
        self.assertTrue(ops_stream[0]["block_num"] >= self.start)
        self.assertTrue(ops_stream[-1]["block_num"] <= self.stop)
        op_stat = b.ops_statistics(start=self.start, stop=self.stop)
        self.assertEqual(op_stat["vote"] + op_stat["transfer"], len(ops_stream))
        ops_blocks = []
        for op in b.blocks(
            start=self.start, stop=self.stop, max_batch_size=self.max_batch_size, threading=False
        ):
            ops_blocks.append(op)
        op_stat4 = {"transfer": 0, "vote": 0}
        self.assertTrue(len(ops_blocks) > 0)
        for block in ops_blocks:
            for tran in block["transactions"]:
                for op in tran["operations"]:
                    if isinstance(op, dict) and "type" in op and "value" in op:
                        op_type = op["type"]
                        if len(op_type) > 10 and op_type[len(op_type) - 10 :] == "_operation":
                            op_type = op_type[:-10]
                        if op_type in opNames:
                            op_stat4[op_type] += 1
                    elif op[0] in opNames:
                        op_stat4[op[0]] += 1
            self.assertTrue(block.identifier >= self.start)
            self.assertTrue(block.identifier <= self.stop)
        self.assertEqual(op_stat["transfer"], op_stat4["transfer"])
        self.assertEqual(op_stat["vote"], op_stat4["vote"])

    def test_stream_batch2(self):
        """
        Test streaming of specific operation types over a fixed block range and verify counts match aggregated statistics.

        Streams "account_create" and "custom_json" operations from block 25097000 to 25097100 (inclusive) using the Blockchain.stream API with a batch size of 50 and single-threaded iteration, collects streamed operations, and asserts:
        - the first streamed operation's block number is >= start block and the last is <= stop block,
        - the sum of the operation counts returned by ops_statistics for "account_create" and "custom_json" equals the number of streamed operations.

        This is a functional test and relies on the shared Hive blockchain instance configured in the test class.
        """
        bts = self.bts
        b = Blockchain(blockchain_instance=bts)
        ops_stream = []
        start_block = 25097000
        stop_block = 25097100
        opNames = ["account_create", "custom_json"]
        for op in b.stream(
            start=int(start_block),
            stop=int(stop_block),
            opNames=opNames,
            max_batch_size=50,
            threading=False,
            thread_num=8,
        ):
            ops_stream.append(op)
        self.assertTrue(ops_stream[0]["block_num"] >= start_block)
        self.assertTrue(ops_stream[-1]["block_num"] <= stop_block)
        op_stat = b.ops_statistics(start=start_block, stop=stop_block)
        self.assertEqual(op_stat["account_create"] + op_stat["custom_json"], len(ops_stream))
