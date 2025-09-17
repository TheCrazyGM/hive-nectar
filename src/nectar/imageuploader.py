# -*- coding: utf-8 -*-
import io
from binascii import hexlify

import requests

from nectar.account import Account
from nectargraphenebase.ecdsasig import sign_message

from .instance import shared_blockchain_instance


class ImageUploader(object):
    def __init__(
        self,
        base_url="https://images.hive.blog",
        challenge="ImageSigningChallenge",
        blockchain_instance=None,
    ):
        """
        Initialize the ImageUploader.
        
        Parameters:
            base_url (str): Base URL of the image upload service (default: "https://images.hive.blog").
            challenge (str): ASCII string prepended to the image bytes when constructing the signing message; ensures signatures are bound to this uploader's purpose.
        
        Notes:
            blockchain_instance is an optional blockchain client; if not provided a shared instance is used.
        """
        self.challenge = challenge
        self.base_url = base_url
        self.blockchain = blockchain_instance or shared_blockchain_instance()

    def upload(self, image, account, image_name=None):
        """
        Upload an image to the configured image service, signing the upload with the account's posting key.
        
        The function accepts a filesystem path (str), raw bytes, or an io.BytesIO for the image. It locates the account's posting private key from the blockchain wallet, signs the image data together with the uploader's challenge string, and POSTs the image under the key `image_name` (defaults to "image") to: <base_url>/<account_name>/<signature_hex>.
        
        Parameters:
            image (str | bytes | io.BytesIO): Path to an image file, raw image bytes, or an in-memory bytes buffer.
            account (str | Account): Account identifier (must have posting permission); used to select the signing key.
            image_name (str, optional): Form field name for the uploaded image (defaults to "image").
        
        Returns:
            dict: Parsed JSON response from the image service.
        
        Raises:
            AssertionError: If the account's posting permission (and therefore a posting key) cannot be accessed.
        """
        account = Account(account, blockchain_instance=self.blockchain)
        if "posting" not in account:
            account.refresh()
        if "posting" not in account:
            raise AssertionError("Could not access posting permission")
        for authority in account["posting"]["key_auths"]:
            posting_wif = self.blockchain.wallet.getPrivateKeyForPublicKey(authority[0])

        if isinstance(image, str):
            image_data = open(image, "rb").read()
        elif isinstance(image, io.BytesIO):
            image_data = image.read()
        else:
            image_data = image

        message = bytes(self.challenge, "ascii") + image_data
        signature = sign_message(message, posting_wif)
        signature_in_hex = hexlify(signature).decode("ascii")

        files = {image_name or "image": image_data}
        url = "%s/%s/%s" % (self.base_url, account["name"], signature_in_hex)
        r = requests.post(url, files=files)
        return r.json()
