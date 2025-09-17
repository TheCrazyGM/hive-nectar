# This Python file uses the following encoding: utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import unittest
from binascii import hexlify

from parameterized import parameterized

import nectargraphenebase.ecdsasig as ecda
from nectargraphenebase.account import PrivateKey

wif = "5J4KCbg1G3my9b9hCaQXnHSm6vrwW9xQTJS6ZciW2Kek7cCkCEk"


class Testcases(unittest.TestCase):
    # Ignore warning:
    # https://www.reddit.com/r/joinmarket/comments/5crhfh/userwarning_implicit_cast_from_char_to_a/
    # @pytest.mark.filterwarnings()
    @parameterized.expand([("cryptography"), ("secp256k1"), ("ecdsa")])
    def test_sign_message(self, module):
        pub_key = bytes(repr(PrivateKey(wif).pubkey), "latin")
        signature = ecda.sign_message("Foobar", wif)
        pub_key_sig = ecda.verify_message("Foobar", signature)
        self.assertEqual(hexlify(pub_key_sig), pub_key)

    @parameterized.expand(
        [
            ("cryptography"),
            ("secp256k1"),
        ]
    )
    def test_sign_message_cross(self, module):
        pub_key = bytes(repr(PrivateKey(wif).pubkey), "latin")
        signature = ecda.sign_message("Foobar", wif)
        pub_key_sig = ecda.verify_message("Foobar", signature)
        self.assertEqual(hexlify(pub_key_sig), pub_key)
        signature = ecda.sign_message("Foobar", wif)
        pub_key_sig = ecda.verify_message("Foobar", signature)
        self.assertEqual(hexlify(pub_key_sig), pub_key)

    @parameterized.expand(
        [
            ("cryptography"),
            ("secp256k1"),
            ("ecdsa"),
        ]
    )
    def test_wrong_signature(self, module):
        pub_key = bytes(repr(PrivateKey(wif).pubkey), "latin")
        signature = ecda.sign_message("Foobar", wif)
        pub_key_sig = ecda.verify_message("Foobar", signature)
        self.assertEqual(hexlify(pub_key_sig), pub_key)
        pub_key_sig2 = ecda.verify_message("Foobar2", signature)
        self.assertTrue(hexlify(pub_key_sig2) != pub_key)


if __name__ == "__main__":
    unittest.main()
