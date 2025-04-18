# -*- coding: utf-8 -*-
import unittest

from nectar import Hive
from nectar.block import Block
from nectar.instance import set_shared_blockchain_instance
from nectar.transactionbuilder import TransactionBuilder
from nectarbase.signedtransactions import Signed_Transaction
from nectargraphenebase.base58 import Base58

from .nodes import get_hive_nodes

wif = "5KQwrPbwdL6PhXujxW37FSSQZ1JiwsST4cqQzDeyXtP79zkvFD3"
wif2 = "5JKu2dFfjKAcD6aP1HqBDxMNbdwtvPS99CaxBzvMYhY94Pt6RDS"
wif3 = "5K1daXjehgPZgUHz6kvm55ahEArBHfCHLy6ew8sT7sjDb76PU2P"


class Testcases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        node_list = get_hive_nodes()
        cls.stm = Hive(
            node=node_list,
            keys={"active": wif, "owner": wif2, "memo": wif3},
            nobroadcast=True,
            num_retries=10,
        )
        cls.steemit = Hive(
            node="https://api.steemit.com",
            nobroadcast=True,
            keys={"active": wif, "owner": wif2, "memo": wif3},
            num_retries=10,
        )
        set_shared_blockchain_instance(cls.stm)
        cls.stm.set_default_account("test")

    def test_emptyTransaction(self):
        stm = self.stm
        tx = TransactionBuilder(steem_instance=stm)
        self.assertTrue(tx.is_empty())
        self.assertTrue(tx["ref_block_num"] is not None)

    def test_verify_transaction(self):
        stm = self.stm
        block = Block(22005665, steem_instance=stm)
        trx = block.transactions[28]
        signed_tx = Signed_Transaction(trx)
        key = signed_tx.verify(chain=stm.chain_params, recover_parameter=False)
        public_key = format(Base58(key[0]), stm.prefix)
        self.assertEqual(public_key, "STM4xA6aCu23rKxsEZWF2xVYJvJAyycuoFxBRQEuQ5Hc7UtFET7fT")
