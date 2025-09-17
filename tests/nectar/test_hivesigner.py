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
        """
        Set up class-wide test fixtures: create a Hive blockchain instance and a test Account.
        
        Initializes a Hive client configured for local testing (no broadcast, unsigned transactions, long refresh interval, and retry settings) using get_hive_nodes(), and attaches an Account named "test" (full access) to that blockchain instance as class attributes.
        """
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

        self.assertEqual(len(url_parts), 3)
        self.assertEqual(len(list(set(url_parts).intersection(set(url_test_parts)))), 3)

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

    def test_sign_method(self):
        """Test the sign method functionality"""
        bts = self.bts
        sc2 = HiveSigner(blockchain_instance=bts)

        # Test transaction to sign
        test_tx = {
            "operations": [
                [
                    "vote",
                    {
                        "voter": "test",
                        "author": "gtg",
                        "permlink": "hive-pressure-4-need-for-speed",
                        "weight": 10000
                    }
                ]
            ]
        }

        # Test signing
        signed_tx = sc2.sign(test_tx)

        # Verify the signed transaction structure
        self.assertIsInstance(signed_tx, dict)
        self.assertIn("operations", signed_tx)
        self.assertIn("signatures", signed_tx)
        self.assertEqual(len(signed_tx["signatures"]), 1)
        self.assertEqual(signed_tx["operations"], test_tx["operations"])

        # Test error cases
        with self.assertRaises(ValueError):
            sc2.sign("not a dict")

        with self.assertRaises(ValueError):
            sc2.sign({})

        with self.assertRaises(ValueError):
            sc2.sign({"operations": []})
