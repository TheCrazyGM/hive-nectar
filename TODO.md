# Cleanup Backlog

Practical refactors to strip legacy branches, rely on the static `nectarapi/openapi.py` map (no bundled JSON specs), and make the codebase type-checkable without changing behavior.

## Models and typing

- Replace `dict` inheritance for `Amount`, `Asset`, `Price`, `BlockchainObject`, and list-like helpers (VotesObject/WitnessesObject) with thin data classes/wrappers; align equality/contains/update semantics to satisfy the type checker and remove LSP violations.
- Tame `asciichart` number handling by rejecting `None` min/max upfront or defaulting them before float math.

## Wallet and storage

- Finish unifying key/token store interfaces (`nectarstorage/interfaces.py` and backends): make `add/delete/getPrivateKeyForPublicKey` signatures match the interfaces, drop dict inheritance, and share encryption/decryption helpers. Introduce a keystore protocol for wallet/transactionbuilder use.

## Tests and docs

- Update docs/examples to describe the single RPC path, static OpenAPI map, and shared-instance/transport lifecycle; prune any references to shipping JSON specs.

## API Refactoring

- Refactor `Account.get_blog` to use `bridge.get_account_posts` (Bridge API) instead of `condenser_api.get_blog`. This aligns with `Discussions_by_blog` but requires changing pagination from index-based (`entry_id`) to cursor-based (`start_author`/`start_permlink`).

## Remove `python-ecdsa`

Goal: eliminate the `ecdsa` runtime dependency while preserving Hive compact signatures, secp256k1 key formatting, BIP32 derivation, memo compatibility, and transaction signing behavior.

### Context

- `python-ecdsa` is currently listed as a hard dependency in `pyproject.toml`.
- Signing already uses `cryptography` in `src/nectargraphenebase/ecdsasig.py`, but several paths still depend on `ecdsa` for secp256k1 point math, signature recovery, DER parsing, and BIP32 key objects.
- `cryptography` covers private-key construction, ECDSA signing, verification, public-key serialization, and DER signature encode/decode.
- `cryptography` does not expose generic secp256k1 point addition or public-key recovery, so Hive-specific compact signature recovery and BIP32 public derivation need a small internal secp256k1 math layer or another maintained library.

### Phase 0: Immediate Mitigation

- Pin `ecdsa` to a non-vulnerable version while removal work is in progress.
- Update `pyproject.toml` from `ecdsa` to a minimum safe version, then refresh `uv.lock`.
- Run the signing, transaction, memo, and BIP32 tests to confirm no resolver regression.

Suggested command:

```sh
uv lock
uv run pytest tests/nectargraphene/test_ecdsa.py tests/nectargraphene/test_bip32.py tests/nectarbase/test_transactions.py tests/nectarbase/test_memo.py
```

### Phase 1: Create Internal secp256k1 Helpers

- Move the pure-Python secp256k1 constants and helpers out of `src/nectargraphenebase/account.py` into a dedicated module, for example `src/nectargraphenebase/secp256k1.py`.
- Include helpers for:
  - curve constants: `P`, `A`, `B`, `N`, `G`
  - modular inverse
  - point validation
  - point addition
  - scalar multiplication
  - compressed point encoding
  - compressed point decoding
  - uncompressed point encoding
  - fixed-width integer-to-bytes conversion
- Keep this module private and narrow. It should only implement the operations Hive-Nectar needs, not a general crypto framework.
- Add direct tests for known compressed/uncompressed keys, tweak-add behavior, invalid point rejection, infinity handling, and public key derivation from a known private scalar.

Primary files:

- `src/nectargraphenebase/account.py`
- `tests/test_tweak_add.py`
- `tests/test_ec_basic.py`
- `tests/test_add_basic.py`

### Phase 2: Remove `ecdsa` From Account/PublicKey Code

- Replace `ecdsa.VerifyingKey.from_string(...)` in `PublicKey.__init__` with internal uncompressed point parsing and compression.
- Replace `PublicKey._derive_y_from_x` with the internal compressed-point decode logic.
- Replace `PublicKey.point()` with a tuple-based internal representation or remove call sites that require the old `ecdsa` point object.
- Replace `PublicKey.from_privkey()` with `cryptography.ec.derive_private_key(..., ec.SECP256K1()).public_key().public_numbers()`.
- Replace `ecdsa.util.number_to_string` with `int.to_bytes(32, "big")`.

Primary file:

- `src/nectargraphenebase/account.py`

Verification:

```sh
uv run pytest tests/nectargraphene/test_key_format.py tests/nectarstorage/test_keystorage.py tests/nectar/test_wallet.py
```

### Phase 3: Remove `ecdsa` From Signature Code

- Replace `ecdsa.util.sigdecode_string` with raw `r = int.from_bytes(sig[:32], "big")` and `s = int.from_bytes(sig[32:], "big")`.
- Replace `ecdsa.util.sigencode_string` with `r.to_bytes(32, "big") + s.to_bytes(32, "big")`.
- Replace `ecdsa.numbertheory.inverse_mod` with the internal modular inverse helper.
- Replace `ecdsa.numbertheory.square_root_mod_prime` with the secp256k1 shortcut `pow(x, (P + 1) // 4, P)`.
- Replace `ecdsa.ellipticcurve.Point` and generator math in `recover_public_key()` with internal tuple-based point math.
- Make `recover_public_key()` return a `cryptography` `EllipticCurvePublicKey` in all successful cases.
- Keep compact signature encoding exactly unchanged: first byte is recovery id plus compressed flag plus compact offset, followed by raw `r || s`.
- Audit the prehashed path in `sign_message()`. It currently signs with `Prehashed(SHA256())`; recovery and verification need to use the same digest semantics.

Primary file:

- `src/nectargraphenebase/ecdsasig.py`

Verification:

```sh
uv run pytest tests/nectargraphene/test_ecdsa.py tests/nectar/test_message.py tests/nectarbase/test_transactions.py
```

### Phase 4: Remove `ecdsa` From Transaction DER Parsing

- Replace `ecdsa.der.remove_sequence/remove_integer` with `cryptography.hazmat.primitives.asymmetric.utils.decode_dss_signature`.
- Preserve the public `derSigToHexSig()` output format: 64 hex chars for `r` plus 64 hex chars for `s`.
- Add or update a test with a known DER signature fixture.

Primary files:

- `src/nectargraphenebase/signedtransactions.py`
- `src/nectargraphenebase/unsignedtransactions.py`

Verification:

```sh
uv run pytest tests/nectarbase/test_transactions.py
```

### Phase 5: Rewrite BIP32 Without `ecdsa`

- Store private keys as raw 32-byte scalars instead of `ecdsa.SigningKey`.
- Store public keys as compressed bytes or internal affine point tuples instead of `ecdsa.VerifyingKey`.
- Replace `SigningKey.from_string(...).get_verifying_key()` with `cryptography` public key derivation or internal scalar multiplication.
- Replace public child derivation `Il * G + K` with internal scalar multiplication plus point addition.
- Replace public extended-key parsing with internal compressed point decode.
- Preserve all existing serialization formats: xprv/xpub, WIF, compressed public key bytes, fingerprint, address, and P2WPKH-over-P2SH address behavior.
- Fix the existing edge check while touching this code: BIP32 requires `Il >= n` to be invalid, not only `Il > n`.

Primary file:

- `src/nectargraphenebase/bip32.py`

Verification:

```sh
uv run pytest tests/nectargraphene/test_bip32.py
```

### Phase 6: Remove Dependency and Compatibility Shims

- Remove `ecdsa` from `pyproject.toml`.
- Refresh `uv.lock`.
- Remove `ecdsa` from `docs/requirements.txt`.
- Update changelog/docs to note that Hive-Nectar no longer uses `python-ecdsa`.
- Run a full import scan and ensure no `ecdsa` import remains outside historical changelog text.

Suggested command:

```sh
rg -n "\becdsa\b|from ecdsa|import ecdsa" src tests docs pyproject.toml
```

### Phase 7: Full Regression Suite

- Run the focused crypto/key tests first.
- Run the full test suite once focused tests pass.
- Manually smoke-test:
  - private key to public key conversion
  - message signing and verification
  - transaction signing and signature recovery
  - memo encode/decode
  - wallet key import and lookup
  - BIP32 path derivation used for Ledger flows

Suggested command:

```sh
uv run pytest
```

### Risk Notes

- The highest-risk areas are compact signature recovery and BIP32 public child derivation because they depend on exact secp256k1 point math that `cryptography` does not expose.
- The signing path is lower risk because it already uses `cryptography`.
- Avoid changing serialized signature, key, address, or extended-key formats in the same patch as dependency removal.
- Keep compatibility tests based on known keys and existing fixtures; any change in derived public keys, WIFs, transaction signatures, or BIP32 outputs should be treated as a regression unless deliberately justified.
