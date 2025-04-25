# This Python file uses the following encoding: utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import unittest

TEST_UNICODE_STR = "ℝεα∂@ßʟ℮ ☂ℯṧт υηḯ¢☺ḓ℮"
# Tk icon as a .gif:
TEST_BYTE_STR = b"GIF89a\x0e\x00\x0b\x00\x80\xff\x00\xff\x00\x00\xc0\xc0\xc0!\xf9\x04\x01\x00\x00\x01\x00,\x00\x00\x00\x00\x0e\x00\x0b\x00@\x02\x1f\x0c\x8e\x10\xbb\xcan\x90\x99\xaf&\xd8\x1a\xce\x9ar\x06F\xd7\xf1\x90\xa1c\x9e\xe8\x84\x99\x89\x97\xa2J\x01\x00;\x1a\x14\x00;;\xba\nD\x14\x00\x00;;"


class Testcases(unittest.TestCase):
    def test_bytes_encoding_arg(self):
        """
        The bytes class has changed in Python 3 to accept an
        additional argument in the constructor: encoding.
        It would be nice to support this without breaking the
        isinstance(..., bytes) test below.
        """
        u = "Unicode string: \u5b54\u5b50"
        b = bytes(u, encoding="utf-8")
        self.assertEqual(b, u.encode("utf-8"))

    def test_bytes_encoding_arg_non_kwarg(self):
        """
        As above, but with a positional argument
        """
        u = "Unicode string: \u5b54\u5b50"
        b = bytes(u, "utf-8")
        self.assertEqual(b, u.encode("utf-8"))

    def test_bytes_int(self):
        """
        In Py3, bytes(int) -> bytes object of size given by the parameter initialized with null
        """
        self.assertEqual(bytes(5), b"\x00\x00\x00\x00\x00")
        # Test using newint:
        self.assertEqual(bytes(int(5)), b"\x00\x00\x00\x00\x00")
        self.assertTrue(isinstance(bytes(int(5)), bytes))

    def test_bytes_iterable_of_ints(self):
        self.assertEqual(bytes([65, 66, 67]), b"ABC")
        self.assertEqual(bytes([int(120), int(121), int(122)]), b"xyz")

    def test_bytes_bytes(self):
        self.assertEqual(bytes(b"ABC"), b"ABC")

    def test_bytes_is_bytes(self):
        b = bytes(b"ABC")
        self.assertTrue(bytes(b) is b)
        self.assertEqual(repr(bytes(b)), "b'ABC'")

    def test_empty_bytes(self):
        b = bytes()
        self.assertEqual(b, b"")

    def test_isinstance_bytes(self):
        self.assertIsInstance(bytes(b"blah"), bytes)

    def test_isinstance_bytes_subclass(self):
        """
        Issue #89
        """
        value = bytes(b"abc")

        class Magic:
            def __bytes__(self):
                return bytes(b"abc")

        self.assertEqual(value, bytes(Magic()))

    def test_isinstance_oldbytestrings_bytes(self):
        """
        Watch out for this. Byte-strings produced in various places in Py2
        are of type 'str'. With 'from future.builtins import bytes', 'bytes'
        is redefined to be a subclass of 'str', not just an alias for 'str'.
        """
        self.assertIsInstance(b"blah", bytes)  # not with the redefined bytes obj
        self.assertIsInstance("blah".encode("utf-8"), bytes)  # not with the redefined bytes obj

    def test_bytes_getitem(self):
        b = bytes(b"ABCD")
        self.assertEqual(b[0], 65)
        self.assertEqual(b[-1], 68)
        self.assertEqual(b[0:1], b"A")
        self.assertEqual(b[:], b"ABCD")

    def test_int(self):
        a = int(5)
        b = int(10)
        self.assertIsInstance(a, int)
        self.assertIsInstance(b, int)

    def test_str(self):
        a = "abc"
        self.assertIsInstance(a, str)

    def test_chr(self):
        BASE58_ALPHABET = b"123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
        self.assertEqual(BASE58_ALPHABET.find(chr(4)), -1)
        self.assertEqual(BASE58_ALPHABET.find(b"Z"), 32)
        self.assertEqual(BASE58_ALPHABET.find(bytes("Z", "ascii")), 32)


if __name__ == "__main__":
    unittest.main()
