# Cleanup Backlog

Practical refactors to strip legacy branches, rely on the static `nectarapi/openapi.py` map (no bundled JSON specs), and make the codebase type-checkable without changing behavior.

## RPC surface
- Flatten RPC callers to a single appbase JSON-RPC shape: drop condenser/appbase flags, retire `call` indirection, and collapse `_check_error_message`/API-probing in `nectarapi/noderpc.py` and `graphenerpc.py` to one path backed by the OpenAPI map.
- Replace the per-process `requests` singleton with a lightweight shared `httpx` client (connection pooling, sane timeouts/retries) and drop the custom `SessionInstance` indirection.
- Simplify node failover: move retry/backoff into one helper used by the RPC layer and `NodeList` instead of scattering error counters and manual `_request_id` handling.
- Route RPC targets through `openapi.get_default_api_for_method` instead of hard-coded `api=` strings in `account.py`, `blockchain.py`, `block.py`, `wallet.py`, `market.py`, and `comment.py`; add a small test to assert `rpcutils.get_query` emits `{}` vs `[]` correctly for mapped APIs.
- Normalize hivemind/bridge usage: ensure follow/reblog/vote lookups consistently hit the mapped bridge or condenser endpoint (no manual fallback branches) and document the canonical call per operation.

## Reward math and chain data
- Deduplicate vote/vesting math: remove legacy steem branches and keep the Hive curve/dust logic in a single helper shared between base and Hive. Guard against `None` dynamic properties.
- Harden block/operation iterators so `block_num` is never `None` before casting and shared pagination code is reused across `blockchain.py`, `block.py`, and history helpers.

## Models and typing
- Replace `dict` inheritance for `Amount`, `Asset`, `Price`, `BlockchainObject`, and list-like helpers (VotesObject/WitnessesObject) with thin data classes/wrappers; align equality/contains/update semantics to satisfy the type checker and remove LSP violations.
- Tame `asciichart` number handling by rejecting `None` min/max upfront or defaulting them before float math.

## Wallet and storage
- Unify key/token store interfaces (`nectarstorage/interfaces.py` and backends): make `add/delete/getPrivateKeyForPublicKey` signatures match the interfaces, drop classmethod `setdefault` overrides, and share encryption/decryption helpers instead of per-store reimplementations. Finish replacing dict inheritance with typed stores.
- Introduce a small keystore protocol used by `wallet.py`/`transactionbuilder.py` so tests can cover wallet behaviors without depending on dict subclasses.

## Tests and docs
- Add targeted tests around the OpenAPI method map (one call per API) to catch regressions when new RPC methods are added.
- Update docs/examples to describe the single RPC path, static openapi map, and removal of condenser/appbase switches; prune any references to shipping JSON specs.
- Untangle shared instance wiring: `nectar/instance.py`’s singleton/config cache should create one `Hive` (and shared httpx client) when `Hive(...)` is instantiated and avoid surprising resets between `shared_blockchain_instance()`, `set_shared_*`, and manual `Hive(keys=[...])` calls; document the lifecycle and make it deterministic.
- Add a small regression test around `shared_blockchain_instance()`/`set_shared_*` ensuring the shared RPC transport is reused when a new Hive is built or injected (no duplicated httpx clients).
