# Cleanup Backlog

Practical refactors to strip legacy branches, rely on the static `nectarapi/openapi.py` map (no bundled JSON specs), and make the codebase type-checkable without changing behavior.

## RPC surface
- Flatten RPC callers to a single appbase JSON-RPC shape: drop condenser/appbase flags, retire `call` indirection, and collapse `_check_error_message`/API-probing in `nectarapi/noderpc.py` and `graphenerpc.py` to one path backed by the OpenAPI map.
- Simplify node failover: move retry/backoff into one helper used by the RPC layer and `NodeList` instead of scattering error counters and manual `_request_id` handling.

## Models and typing
- Replace `dict` inheritance for `Amount`, `Asset`, `Price`, `BlockchainObject`, and list-like helpers (VotesObject/WitnessesObject) with thin data classes/wrappers; align equality/contains/update semantics to satisfy the type checker and remove LSP violations.
- Tame `asciichart` number handling by rejecting `None` min/max upfront or defaulting them before float math.

## Wallet and storage
- Finish unifying key/token store interfaces (`nectarstorage/interfaces.py` and backends): make `add/delete/getPrivateKeyForPublicKey` signatures match the interfaces, drop dict inheritance, and share encryption/decryption helpers. Introduce a keystore protocol for wallet/transactionbuilder use.

## Tests and docs
- Update docs/examples to describe the single RPC path, static OpenAPI map, and shared-instance/transport lifecycle; prune any references to shipping JSON specs.
