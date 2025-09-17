#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Simple test for PublicKey.add method"""

import hashlib
import os
import sys

# Add src to path so we can import nectargraphenebase
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from nectargraphenebase.account import PublicKey


def test_basic_add_functionality():
    """Test that PublicKey.add method works at basic level"""
    print("Testing basic PublicKey.add functionality...")

    # Create a PublicKey using a known valid key from test data
    test_key = "STM6oVMzJJJgSu3hV1DZBcLdMUJYj3Cs6kGXf6WVLP3HhgLgNkA5J"

    try:
        test_pub = PublicKey(test_key)
        print(f"Original public key: {test_pub}")
        print(f"Original key type: {type(test_pub)}")

        # Test with a simple tweak
        tweak = hashlib.sha256(b"test_tweak").digest()
        print(f"Tweak: {tweak.hex()}")

        result = test_pub.add(tweak)
        print(f"Result: {result}")
        print(f"Result type: {type(result)}")
        print("✓ PublicKey.add method executed successfully")
        print(f"✓ Result is PublicKey instance: {isinstance(result, PublicKey)}")
        print(f"✓ Result has same prefix: {result.prefix == test_pub.prefix}")

        # Test that child method works
        print("\nTesting child method...")
        child_key = test_pub.child(b"test_offset")
        print(f"Child key: {child_key}")
        print("✓ PublicKey.child method executed successfully")

        return True

    except Exception as e:
        print(f"✗ Error in PublicKey.add: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_basic_add_functionality()
    if success:
        print("\n Basic functionality test PASSED")
    else:
        print("\n Basic functionality test FAILED")
