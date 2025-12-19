import hashlib
import logging
import struct
from binascii import hexlify
from typing import Any, Callable, Optional, Union

import ecdsa
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import (
    Prehashed,
    decode_dss_signature,
    encode_dss_signature,
)
from ecdsa.ellipticcurve import Point
from ecdsa.numbertheory import inverse_mod, square_root_mod_prime
from ecdsa.util import number_to_string, sigdecode_string, sigencode_string, string_to_number

from .account import PrivateKey, PublicKey

log = logging.getLogger(__name__)


def _is_canonical(sig: Union[bytes, bytearray]) -> bool:
    """
    Return True if a 64-byte ECDSA signature (R || S) is in canonical form.

    A canonical signature here means:
    - Neither R nor S has its highest bit set (no negative integers when interpreted as signed big-endian).
    - Neither R nor S has unnecessary leading zero bytes (no extra 0x00 padding before a non-negative highest byte).

    Parameters:
        sig (bytes or bytearray): 64-byte concatenation of R (32 bytes) followed by S (32 bytes).

    Returns:
        bool: True if signature is canonical, False otherwise.
    """
    sig = bytearray(sig)
    return (
        not (int(sig[0]) & 0x80)
        and not (sig[0] == 0 and not (int(sig[1]) & 0x80))
        and not (int(sig[32]) & 0x80)
        and not (sig[32] == 0 and not (int(sig[33]) & 0x80))
    )


def compressedPubkey(pk: Union[ecdsa.keys.VerifyingKey, Any]) -> bytes:
    """
    Return the 33-byte compressed secp256k1 public key for the given public-key object.

    Accepts either an ecdsa.keys.VerifyingKey or an object exposing public_numbers().x and .y
    (such as a cryptography EllipticCurvePublicKey). The output is 1 byte (0x02 if y is even,
    0x03 if y is odd) followed by the 32-byte big-endian X coordinate.

    Parameters:
        pk: Public-key object (ecdsa.VerifyingKey or object with public_numbers().x and .y).

    Returns:
        bytes: 33-byte compressed public key (prefix + 32-byte X).
    """
    if isinstance(pk, ecdsa.keys.VerifyingKey):
        order = ecdsa.SECP256k1.order
        # Get the curve point from VerifyingKey
        try:
            # Try newer ecdsa version approach
            point = pk.point  # type: ignore[attr-defined]
        except AttributeError:
            # Fallback for older versions
            point = pk.pubkey.point  # type: ignore[attr-defined]
        x = point.x()
        y = point.y()
    elif isinstance(pk, PublicKey):
        # Handle account.PublicKey type
        order = ecdsa.SECP256k1.order
        point = pk.point()
        x = point.x()
        y = point.y()
    else:
        order = ecdsa.SECP256k1.order
        x = pk.public_numbers().x
        y = pk.public_numbers().y
    x_str = number_to_string(x, order)
    return bytes(chr(2 + (y & 1)), "ascii") + x_str


def recover_public_key(
    digest: bytes, signature: bytes, i: int, message: Optional[bytes] = None
) -> Union[ecdsa.keys.VerifyingKey, ec.EllipticCurvePublicKey, None]:
    """
    Recover the secp256k1 public key from an ECDSA signature and message hash.

    If `message` is provided the function will construct a cryptography EllipticCurvePublicKey
    from the recovered point and verify the signature against the message; on success it
    returns that cryptography public key. If `message` is None the function returns an
    ecdsa.VerifyingKey built from the recovered point after verifying the signature
    against the provided digest. If verification fails, returns None (when `message` is None)
    or raises a verification exception (when `message` is provided).

    Parameters:
        digest (bytes): The message hash (big-endian) used when signing.
        signature (bytes): 64-byte signature consisting of r||s (raw concatenation).
        i (int): Recovery identifier (0..3) selecting which of the possible curve points to use.
        message (bytes or str, optional): Original message to verify against; if a str it is
            encoded as UTF-8. When provided the function returns a cryptography public key
            and performs verification using ECDSA-SHA256.

    Returns:
        cryptography.hazmat.primitives.asymmetric.ec.EllipticCurvePublicKey
            when `message` is provided and verification succeeds;
        ecdsa.keys.VerifyingKey
            when `message` is None and digest-based verification succeeds;
        None
            when `message` is None and verification fails.

    Raises:
        cryptography.exceptions.InvalidSignature: If `message` is provided and signature verification fails.
    """

    # See http: //www.secg.org/download/aid-780/sec1-v2.pdf section 4.1.6 primarily
    curve = ecdsa.SECP256k1.curve
    G = ecdsa.SECP256k1.generator
    order = ecdsa.SECP256k1.order
    yp = i % 2
    r, s = sigdecode_string(signature, order)
    # 1.1
    x = r + (i // 2) * order
    # 1.3. This actually calculates for either effectively 02||X or 03||X depending on 'k' instead of always for 02||X as specified.
    # This substitutes for the lack of reversing R later on. -R actually is defined to be just flipping the y-coordinate in the elliptic curve.
    alpha = ((x * x * x) + (curve.a() * x) + curve.b()) % curve.p()
    beta = square_root_mod_prime(alpha, curve.p())
    y = beta if (beta - yp) % 2 == 0 else curve.p() - beta
    # 1.4 Constructor of Point is supposed to check if nR is at infinity.
    R = Point(curve, x, y, order)
    # 1.5 Compute e
    e = string_to_number(digest)
    # 1.6 Compute Q = r^-1(sR - eG)
    Q = inverse_mod(r, order) * (s * R + (-e % order) * G)

    if message is not None:
        if not isinstance(message, bytes):
            message = bytes(message, "utf-8")
        sigder = encode_dss_signature(r, s)
        Q_point = Q.to_affine()  # type: ignore[attr-defined]
        public_key = ec.EllipticCurvePublicNumbers(
            Q_point.x(), Q_point.y(), ec.SECP256K1()
        ).public_key(default_backend())
        public_key.verify(sigder, message, ec.ECDSA(hashes.SHA256()))
        return public_key
    else:
        # Not strictly necessary, but let's verify the message for paranoia's sake.
        if not ecdsa.VerifyingKey.from_public_point(Q, curve=ecdsa.SECP256k1).verify_digest(
            signature, digest, sigdecode=sigdecode_string
        ):
            return None
        return ecdsa.VerifyingKey.from_public_point(Q, curve=ecdsa.SECP256k1)


def recoverPubkeyParameter(
    message: Optional[Union[str, bytes]],
    digest: bytes,
    signature: bytes,
    pubkey: Union[PublicKey, ec.EllipticCurvePublicKey],
) -> Optional[int]:
    """
    Determine the ECDSA recovery parameter (0–3) that, when used with the given digest and 64-byte signature (R||S), reproduces the provided public key.

    Attempts each recovery index i in 0..3, recovers a candidate public key, and compares its compressed form to the compressed form of the supplied pubkey. If a match is found returns the matching index; otherwise returns None.

    Parameters that need clarification:
    - message: the original message (will be encoded as UTF-8 if not bytes) and is used when recovering a cryptography public key variant.
    - digest: the message hash used for recovery.
    - signature: 64-byte R||S signature (bytes-like).
    - pubkey: the expected public key to match; may be a cryptography/ec or ecdsa-like public key object.

    Returns:
        int: matching recovery parameter in 0..3, or None if no match is found.
    """
    if not isinstance(message, bytes):
        if message is None:
            message = b""
        else:
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
            if p is None:
                continue
            p_comp = hexlify(compressedPubkey(p))
            p_string = hexlify(p.to_string())  # type: ignore[attr-defined]
            if isinstance(pubkey, PublicKey):
                pubkey_string = bytes(repr(pubkey), "latin")
            else:  # pragma: no cover
                pubkey_string = hexlify(pubkey.to_string())  # type: ignore[attr-defined]
            if p_string == pubkey_string or p_comp == pubkey_string:
                return i
    return None


def sign_message(message: Union[str, bytes], wif: str, hashfn: Callable = hashlib.sha256) -> bytes:
    """
    Sign a message using a private key in Wallet Import Format (WIF) and return a compact, canonical ECDSA signature.

    Signs the provided message with secp256k1 ECDSA-SHA256 using the private key derived from the given WIF. The function repeats signing as needed until it produces a canonical 64-byte R||S signature (both R and S encoded as 32 bytes). It also computes the recovery parameter for the signature and encodes it into the first byte of the returned blob.

    Parameters:
        message (bytes or str): Message to sign. If a str is provided it is encoded as UTF-8 before hashing.
        wif (str): Private key in Wallet Import Format (WIF).
        hashfn (callable, optional): Hash function to apply to the message prior to recovery-parameter computation; defaults to hashlib.sha256.

    Returns:
        bytes: 65-byte compact signature: 1-byte recovery/version prefix (recovery parameter adjusted for compact/compressed form) followed by the 64-byte R||S sequence.
    """

    if not isinstance(message, bytes):
        message = bytes(message, "utf-8")

    # Detect if message is already a digest
    prehashed = len(message) == hashfn().digest_size

    if prehashed:
        digest = message
        message_for_signing = message  # the digest
        algorithm_for_signing = ec.ECDSA(Prehashed(hashes.SHA256()))
        message_for_recovery = None
    else:
        digest = hashfn(message).digest()
        message_for_signing = message
        algorithm_for_signing = ec.ECDSA(hashes.SHA256())
        message_for_recovery = message

    priv_key = PrivateKey(wif)
    cnt = 0
    private_key = ec.derive_private_key(int(repr(priv_key), 16), ec.SECP256K1(), default_backend())
    public_key = private_key.public_key()
    while True:
        cnt += 1
        if not cnt % 20:
            log.info("Still searching for a canonical signature. Tried %d times already!" % cnt)
        order = ecdsa.SECP256k1.order
        sigder = private_key.sign(message_for_signing, algorithm_for_signing)
        r, s = decode_dss_signature(sigder)
        signature = sigencode_string(r, s, order)
        # Make sure signature is canonical!
        #
        sigder = bytearray(sigder)
        lenR = sigder[3]
        lenS = sigder[5 + lenR]
        if lenR == 32 and lenS == 32 and _is_canonical(signature):
            # Derive the recovery parameter
            #
            i = recoverPubkeyParameter(message_for_recovery, digest, signature, public_key)
            if i is None:
                continue
            i += 4  # compressed
            i += 27  # compact
            break

    # pack signature
    #
    sigstr = struct.pack("<B", i)
    sigstr += signature

    return sigstr


def verify_message(
    message: Union[str, bytes],
    signature: Union[str, bytes],
    hashfn: Callable = hashlib.sha256,
    recover_parameter: Optional[int] = None,
) -> Optional[bytes]:
    """
    Verify an ECDSA secp256k1 signature against a message and return the signer's compressed public key.

    Parameters:
        message (bytes or str): The message to verify. If a str, it will be UTF-8 encoded.
        signature (bytes or str): 65-byte compact signature where the first byte encodes the recovery parameter/version and the remaining 64 bytes are R||S. If a str, it will be UTF-8 encoded.
        hashfn (callable): Hash function constructor used to compute the digest of the message (default: hashlib.sha256).
        recover_parameter (int, optional): Explicit recovery parameter (0–3). If omitted, it is extracted from the signature's first byte.

    Returns:
        bytes: The 33-byte compressed public key of the recovered signer on successful verification.

    Notes:
        - The function computes the digest of `message` with `hashfn`, recovers the public key using the recovery parameter, converts the 64-byte R||S into DER form, and verifies the signature with ECDSA-SHA256.
        - If the recovery parameter cannot be determined from the signature, None is returned.
        - Cryptographic verification errors (e.g., invalid signature) will propagate as raised exceptions.
    """
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
    r, s = sigdecode_string(sig, order)
    sigder = encode_dss_signature(r, s)
    p.verify(sigder, digest, ec.ECDSA(Prehashed(hashes.SHA256())))  # type: ignore[attr-defined]
    phex = compressedPubkey(p)
    return phex
