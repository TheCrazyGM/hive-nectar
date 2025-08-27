# -*- coding: utf-8 -*-
import unittest

from nectar import Hive
from nectar.account import Account
from nectar.hivesigner import HiveSigner

from .nodes import get_hive_nodes

# Py3 compatibility
core_unit = "STM"


class Testcases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bts = Hive(
            node=get_hive_nodes(),
            nobroadcast=True,
            unsigned=True,
            data_refresh_time_seconds=900,
            num_retries=10,
        )

        cls.account = Account("test", full=True, blockchain_instance=cls.bts)

    def test_transfer(self):
        bts = self.bts
        acc = self.account
        acc.blockchain.txbuffer.clear()
        tx = acc.transfer("test1", 1.000, "HIVE", memo="test")
        sc2 = HiveSigner(blockchain_instance=bts)
        url = sc2.url_from_tx(tx)
        url_test = (
            "https://hivesigner.com/sign/transfer?from=test&to=test1&amount=1.000+HIVE&memo=test"
        )
        self.assertEqual(len(url), len(url_test))
        self.assertEqual(len(url.split("?")), 2)
        self.assertEqual(url.split("?")[0], url_test.split("?")[0])

        url_parts = (url.split("?")[1]).split("&")
        url_test_parts = (url_test.split("?")[1]).split("&")

        self.assertEqual(len(url_parts), 4)
        self.assertEqual(len(list(set(url_parts).intersection(set(url_test_parts)))), 4)

    def test_login_url(self):
        bts = self.bts
        sc2 = HiveSigner(blockchain_instance=bts)
        url = sc2.get_login_url("localhost", scope="login,vote")
        url_test = "https://hivesigner.com/oauth2/authorize?client_id=None&redirect_uri=localhost&scope=login,vote"
        self.assertEqual(len(url), len(url_test))
        self.assertEqual(len(url.split("?")), 2)
        self.assertEqual(url.split("?")[0], url_test.split("?")[0])

        url_parts = (url.split("?")[1]).split("&")
        url_test_parts = (url_test.split("?")[1]).split("&")

        self.assertEqual(len(url_parts), 3)
        self.assertEqual(len(list(set(url_parts).intersection(set(url_test_parts)))), 3)
