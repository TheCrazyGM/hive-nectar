import base64
import hashlib
from typing import Any

from Cryptodome import Random
from Cryptodome.Cipher import AES


class AESCipher:
    """
    A classical AES Cipher. Can use any size of data and any size of password thanks to padding.
    Also ensure the coherence and the type of the data with a unicode to byte converter.
    """

    def __init__(self, key: Any) -> None:
        self.bs: int = 32
        self.key = hashlib.sha256(AESCipher.str_to_bytes(key)).digest()

    @staticmethod
    def str_to_bytes(data: Any) -> bytes:
        u_type = type(b"".decode("utf8"))
        if isinstance(data, u_type):
            return data.encode("utf8")
        return data

    def _pad(self, s: bytes) -> bytes:
        return s + (self.bs - len(s) % self.bs) * AESCipher.str_to_bytes(
            chr(self.bs - len(s) % self.bs)
        )

    @staticmethod
    def _unpad(s: bytes) -> bytes:
        return s[: -ord(s[len(s) - 1 :])]

    def encrypt(self, raw: Any) -> str:
        raw = self._pad(AESCipher.str_to_bytes(raw))
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return base64.b64encode(iv + cipher.encrypt(raw)).decode("utf-8")

    def decrypt(self, enc: str) -> str:
        enc_bytes = base64.b64decode(enc)
        iv = enc_bytes[: AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return self._unpad(cipher.decrypt(enc_bytes[AES.block_size :])).decode("utf-8")
