#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test HiveSigner integration in TransactionBuilder"""

import os
import sys
import unittest
from unittest.mock import Mock, patch

# Add src to path so we can import nectargraphenebase
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from nectar.transactionbuilder import TransactionBuilder


class TestHiveSignerIntegration(unittest.TestCase):
    """Test HiveSigner integration in TransactionBuilder"""

    def setUp(self):
        """Set up test fixtures"""
        # Mock blockchain instance
        self.mock_blockchain = Mock()
        self.mock_blockchain.prefix = "STM"
        self.mock_blockchain.use_hs = False
        self.mock_blockchain.hivesigner = None
        self.mock_blockchain.wallet = Mock()
        self.mock_blockchain.wallet.locked.return_value = False

        # Create TransactionBuilder with mock blockchain
        self.tx_builder = TransactionBuilder(blockchain_instance=self.mock_blockchain)
        self.tx_builder.appendOps({"type": "transfer", "data": {}})  # Add dummy operation

    def test_append_signer_restricts_permissions_with_hivesigner(self):
        """Test that appendSigner restricts permissions when using HiveSigner"""
        # Setup HiveSigner
        self.mock_blockchain.use_hs = True
        self.mock_blockchain.hivesigner = Mock()
        self.mock_blockchain.hivesigner.set_username = Mock()

        # Mock account
        mock_account = Mock()
        mock_account.__getitem__ = Mock(return_value={"name": "testuser"})

        with patch("nectar.transactionbuilder.Account", return_value=mock_account):
            # Should work with posting permission
            self.tx_builder.appendSigner("testuser", "posting")
            self.mock_blockchain.hivesigner.set_username.assert_called_with("testuser", "posting")

            # Should raise ValueError for non-posting permissions
            with self.assertRaises(ValueError) as cm:
                self.tx_builder.appendSigner("testuser", "active")
            self.assertIn("HiveSigner only supports 'posting' permission", str(cm.exception))

            with self.assertRaises(ValueError) as cm:
                self.tx_builder.appendSigner("testuser", "owner")
            self.assertIn("HiveSigner only supports 'posting' permission", str(cm.exception))

    def test_sign_method_uses_hivesigner_when_enabled(self):
        """Test that sign() method uses HiveSigner when enabled"""
        # Setup HiveSigner
        self.mock_blockchain.use_hs = True
        self.mock_blockchain.hivesigner = Mock()
        mock_signed_tx = {"signatures": ["sig1", "sig2"]}
        self.mock_blockchain.hivesigner.sign.return_value = mock_signed_tx

        # Mock transaction construction
        self.tx_builder.constructTx = Mock()
        self.tx_builder._is_constructed = Mock(return_value=True)

        # Call sign method
        result = self.tx_builder.sign()

        # Verify HiveSigner.sign was called
        self.mock_blockchain.hivesigner.sign.assert_called_once_with(self.tx_builder.json())
        self.assertEqual(self.tx_builder["signatures"], ["sig1", "sig2"])
        self.assertIsInstance(result, dict)

    def test_broadcast_method_uses_hivesigner_when_enabled(self):
        """Test that broadcast() method uses HiveSigner when enabled"""
        # Setup HiveSigner
        self.mock_blockchain.use_hs = True
        self.mock_blockchain.hivesigner = Mock()
        mock_broadcast_result = {"success": True, "trx_id": "12345"}
        self.mock_blockchain.hivesigner.broadcast.return_value = mock_broadcast_result

        # Mock signing
        self.tx_builder._is_signed = Mock(return_value=True)
        # Add a signing account for username
        self.tx_builder.signing_accounts = ["testuser"]

        # Stub builder methods used by broadcast
        self.tx_builder.json = Mock(
            return_value={"operations": [{"type": "transfer", "data": {}}]}
        )
        self.tx_builder.clear = Mock()

        # Call broadcast method
        self.tx_builder.broadcast()

        # Verify HiveSigner.broadcast was called with operations list and username
        expected_operations = self.tx_builder.json()["operations"]
        self.mock_blockchain.hivesigner.broadcast.assert_called_once_with(
            expected_operations, username="testuser"
        )
        self.tx_builder.clear.assert_called_once()

    def test_fallback_to_regular_signing_when_hivesigner_fails(self):
        """Test that sign() falls back to regular signing when HiveSigner fails"""
        # Setup HiveSigner that fails
        self.mock_blockchain.use_hs = True
        self.mock_blockchain.hivesigner = Mock()
        self.mock_blockchain.hivesigner.sign.side_effect = Exception("HiveSigner error")

        # Setup regular signing mocks
        self.tx_builder.wifs = {"wif1"}
        self.tx_builder.tx = Mock()
        self.tx_builder.tx.sign = Mock()
        self.tx_builder.tx.json.return_value = {"signatures": ["regular_sig"]}

        # Mock transaction construction
        self.tx_builder.constructTx = Mock()
        self.tx_builder._is_constructed = Mock(return_value=True)

        # Call sign method
        _ = self.tx_builder.sign()

        # Verify regular signing was used as fallback
        self.tx_builder.tx.sign.assert_called_once()
        self.assertIn("regular_sig", self.tx_builder["signatures"])

    def test_fallback_to_regular_broadcast_when_hivesigner_fails(self):
        """Test that broadcast() falls back to regular RPC when HiveSigner fails"""
        # Setup HiveSigner that fails
        self.mock_blockchain.use_hs = True
        self.mock_blockchain.hivesigner = Mock()
        self.mock_blockchain.hivesigner.broadcast.side_effect = Exception("HiveSigner error")

        # Setup regular broadcast mocks
        self.mock_blockchain.nobroadcast = False
        self.mock_blockchain.rpc = Mock()
        self.mock_blockchain.rpc.broadcast_transaction = Mock()

        # Mock signing
        self.tx_builder._is_signed = Mock(return_value=True)

        # Call broadcast method
        self.tx_builder.broadcast()

        # Verify regular RPC broadcast was used as fallback
        self.mock_blockchain.rpc.broadcast_transaction.assert_called_once()


if __name__ == "__main__":
    unittest.main()
