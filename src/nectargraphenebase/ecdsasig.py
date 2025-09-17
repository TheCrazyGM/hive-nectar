# -*- coding: utf-8 -*-
import hashlib
import logging
import struct
from binascii import hexlify

import ecdsa
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import (
    decode_dss_signature,
    encode_dss_signature,
)

from .account import PrivateKey, PublicKey

log = logging.getLogger(__name__)


def _is_canonical(sig):
    sig = bytearray(sig)
    return (
        not (int(sig[0]) & 0x80)
        and not (sig[0] == 0 and not (int(sig[1]) & 0x80))
        and not (int(sig[32]) & 0x80)
        and not (sig[32] == 0 and not (int(sig[33]) & 0x80))
    )


def compressedPubkey(pk):
    if not isinstance(pk, ecdsa.keys.VerifyingKey):
        order = ecdsa.SECP256k1.order
        x = pk.public_numbers().x
        y = pk.public_numbers().y
    else:
        order = pk.curve.generator.order()
        p = pk.pubkey.point
        x = p.x()
        y = p.y()
    x_str = ecdsa.util.number_to_string(x, order)
    return bytes(chr(2 + (y & 1)), "ascii") + x_str


def recover_public_key(digest, signature, i, message=None):
    """Recover the public key from the the signature"""

    # See http: //www.secg.org/download/aid-780/sec1-v2.pdf section 4.1.6 primarily
    curve = ecdsa.SECP256k1.curve
    G = ecdsa.SECP256k1.generator
    order = ecdsa.SECP256k1.order
    yp = i % 2
    r, s = ecdsa.util.sigdecode_string(signature, order)
    # 1.1
    x = r + (i // 2) * order
    # 1.3. This actually calculates for either effectively 02||X or 03||X depending on 'k' instead of always for 02||X as specified.
    # This substitutes for the lack of reversing R later on. -R actually is defined to be just flipping the y-coordinate in the elliptic curve.
    alpha = ((x * x * x) + (curve.a() * x) + curve.b()) % curve.p()
    beta = ecdsa.numbertheory.square_root_mod_prime(alpha, curve.p())
    y = beta if (beta - yp) % 2 == 0 else curve.p() - beta
    # 1.4 Constructor of Point is supposed to check if nR is at infinity.
    R = ecdsa.ellipticcurve.Point(curve, x, y, order)
    # 1.5 Compute e
    e = ecdsa.util.string_to_number(digest)
    # 1.6 Compute Q = r^-1(sR - eG)
    Q = ecdsa.numbertheory.inverse_mod(r, order) * (s * R + (-e % order) * G)

    if message is not None:
        if not isinstance(message, bytes):
            message = bytes(message, "utf-8")
        sigder = encode_dss_signature(r, s)
        try:
            Q_point = Q.to_affine()
            public_key = ec.EllipticCurvePublicNumbers(
                Q_point.x(), Q_point.y(), ec.SECP256K1()
            ).public_key(default_backend())
        except Exception:
            try:
                public_key = ec.EllipticCurvePublicNumbers(
                    Q._Point__x, Q._Point__y, ec.SECP256K1()
                ).public_key(default_backend())
            except Exception:
                Q_point = Q.to_affine()
                public_key = ec.EllipticCurvePublicNumbers(
                    int(Q_point.x()), int(Q_point.y()), ec.SECP256K1()
                ).public_key(default_backend())
        public_key.verify(sigder, message, ec.ECDSA(hashes.SHA256()))
        return public_key
    else:
        # Not strictly necessary, but let's verify the message for paranoia's sake.
        if not ecdsa.VerifyingKey.from_public_point(Q, curve=ecdsa.SECP256k1).verify_digest(
            signature, digest, sigdecode=ecdsa.util.sigdecode_string
        ):
            return None
        return ecdsa.VerifyingKey.from_public_point(Q, curve=ecdsa.SECP256k1)


def recoverPubkeyParameter(message, digest, signature, pubkey):
    """Use to derive a number that allows to easily recover the
    public key from the signature
    """
    if not isinstance(message, bytes):
        message = bytes(message, "utf-8")
    for i in range(0, 4):
        if not isinstance(pubkey, PublicKey):
            p = recover_public_key(digest, signature, i, message)
            p_comp = hexlify(compressedPubkey(p))
            pubkey_comp = hexlify(compressedPubkey(pubkey))
            if p_comp == pubkey_comp:
                return i
        else:  # pragma: no cover
            p = recover_public_key(digest, signature, i)
            p_comp = hexlify(compressedPubkey(p))
            p_string = hexlify(p.to_string())
            if isinstance(pubkey, PublicKey):
                pubkey_string = bytes(repr(pubkey), "latin")
            else:  # pragma: no cover
                pubkey_string = hexlify(pubkey.to_string())
            if p_string == pubkey_string or p_comp == pubkey_string:
                return i
    return None


def sign_message(message, wif, hashfn=hashlib.sha256):
    """Sign a digest with a wif key

    :param str wif: Private key in
    """

    if not isinstance(message, bytes):
        message = bytes(message, "utf-8")

    digest = hashfn(message).digest()
    priv_key = PrivateKey(wif)
    cnt = 0
    private_key = ec.derive_private_key(
        int(repr(priv_key), 16), ec.SECP256K1(), default_backend()
    )
    public_key = private_key.public_key()
    while True:
        cnt += 1
        if not cnt % 20:
            log.info("Still searching for a canonical signature. Tried %d times already!" % cnt)
        order = ecdsa.SECP256k1.order
        sigder = private_key.sign(message, ec.ECDSA(hashes.SHA256()))
        r, s = decode_dss_signature(sigder)
        signature = ecdsa.util.sigencode_string(r, s, order)
        # Make sure signature is canonical!
        #
        sigder = bytearray(sigder)
        lenR = sigder[3]
        lenS = sigder[5 + lenR]
        if lenR == 32 and lenS == 32:
            # Derive the recovery parameter
            #
            i = recoverPubkeyParameter(message, digest, signature, public_key)
            i += 4  # compressed
            i += 27  # compact
            break

    # pack signature
    #
    sigstr = struct.pack("<B", i)
    sigstr += signature

    return sigstr


def verify_message(message, signature, hashfn=hashlib.sha256, recover_parameter=None):
    if not isinstance(message, bytes):
        message = bytes(message, "utf-8")
    if not isinstance(signature, bytes):
        signature = bytes(signature, "utf-8")
    if not isinstance(message, bytes):
        raise AssertionError()
    if not isinstance(signature, bytes):
        raise AssertionError()
    digest = hashfn(message).digest()
    sig = signature[1:]
    if recover_parameter is None:
        recover_parameter = bytearray(signature)[0] - 4 - 27  # recover parameter only
    if recover_parameter < 0:
        log.info("Could not recover parameter")
        return None

    p = recover_public_key(digest, sig, recover_parameter, message)
    order = ecdsa.SECP256k1.order
    r, s = ecdsa.util.sigdecode_string(sig, order)
    sigder = encode_dss_signature(r, s)
    p.verify(sigder, message, ec.ECDSA(hashes.SHA256()))
    phex = compressedPubkey(p)

    return phex
