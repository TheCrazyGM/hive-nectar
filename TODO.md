# Hive-only Refactor Plan

Goal: Remove all references to Steem and Blurt and make the project Hive-only while preserving public API stability where sensible.

## Scope overview

- __Code__: Remove `steem` and `blurt` modules and all branching for those chains.
- __CLI__: Restrict to Hive; simplify flags/options and defaults.
- __Chain config__: Prune non-Hive entries from `known_chains`.
- __Docs/Examples__: Update or delete Steem/Blurt content.
- __Tests__: Remove/adjust tests tied to Steem/Blurt.
- __Config/UX__: Migrate settings to Hive-only and provide smooth upgrade.

## Plan of attack (checklist)

### 1) Core modules and APIs

- [ ] Remove `src/nectar/steem.py` and `src/nectar/blurt.py` (or mark deprecated with runtime error if a soft removal is preferred initially).
- [ ] Ensure all imports referencing `nectar.steem` and `nectar.blurt` are removed or redirected. Example: `src/nectar/cli.py` imports `Steem` and `Blurt`.
- [ ] Audit utility/constants referencing Steem names (e.g., `STEEM_100_PERCENT`, `STEEM_VOTE_REGENERATION_SECONDS`) and rename to chain-neutral or Hive-specific (`HIVE_100_PERCENT`, etc.). Update call sites.
- [ ] In `src/nectar/blockchaininstance.py` and dependent types, remove any multi-chain logic that’s only for Steem/Blurt; keep Hive logic and neutral abstractions.
- [x] Purge STEEM/SBD mentions and modernize docs in account module (`src/nectar/account.py`).

### 2) Chain selection and CLI simplification

- [ ] In `src/nectar/cli.py`:
  - [x] Remove `--steem`, `--blurt`, and any branching that selects those chains. (Hive-only instance)
  - [x] Remove asset callback options for STEEM/SBD/BLURT. Keep only `HIVE/HBD/TESTS/TBD` as appropriate.
  - [x] Remove `steemconnect`/`use_sc2` branches; keep `hivesigner`/`use_hs` only. (legacy keys map to HiveSigner)
  - [x] Simplify `updatenodes` subcommand: drop `--steem`/`--blurt`, and code paths that use those lists.
  - [x] Update `currentnode`/`nextnode` outputs that mention Steem to Hive-only verbiage.
- [ ] In `src/nectar/instance.py`/`src/nectar/blockchaininstance.py`, enforce Hive as the only chain; remove config fallback to steem/blurt.

### 3) Chain parameters and node list

- [ ] In `src/nectargraphenebase/chains.py`, prune `known_chains` to only Hive variants (e.g., `HIVE`, `HIVE2`, `TESTNET/TESTDEV` if kept) and remove `STEEM`, `BLURT`, and unrelated forks.
- [ ] In `src/nectar/nodelist.py`, remove Steem/Blurt node providers and outputs; keep Hive node discovery only.

### 4) Config and migration

- [x] In config defaults (e.g., `get_default_config_store()` and related), set `default_chain` to `hive` and remove acceptance of `steem` or `blurt`.
- [ ] On startup, if user config contains `default_chain` in {"steem","blurt"}, log a warning and auto-migrate to `hive`.
- [x] Migrate `steemconnect` variables (`sc2_api_url`, etc.) to HiveSigner equivalents; keep `hs_api_url`/`hs_oauth_base_url` (map legacy keys).

### 5) Public documentation and examples

- [ ] Remove generated docs for `nectar.steem` and `nectar.blurt`. Update `.rst` sources that reference them.
- [ ] Update tutorials (`docs/tutorials.rst`, CLI docs) to remove multi-chain instructions and examples.
- [ ] Update examples under `examples/` that use Steem/Blurt to Hive-only or delete them.
- [ ] Update `README.md` messaging to Hive-only branding and features.

### 6) Tests

- [ ] Remove tests that target Blurt/Steem specifically (e.g., `tests/nectar/test_account_blurt.py`).
- [ ] Update tests that assert chain selection or symbols (SBD/STEEM) to HBD/HIVE.
- [ ] Ensure market/price tests (`src/nectar/market.py`, `src/nectar/price.py` call sites) reference Hive assets only.

### 7) Packaging and CI

- [ ] Bump version and add CHANGELOG entry describing the breaking change (Hive-only).
- [ ] Adjust any classifiers/metadata that mention Steem/Blurt.
- [ ] Run full test suite and docs build; fix fallout.

## Sequenced execution

1. Code-only pruning behind feature flag (optional): deprecate imports of `nectar.steem`/`nectar.blurt` raising clear ImportError with guidance; keep build green.
2. CLI and config simplification; ensure local runs still work.
3. Prune chain tables and node logic; run unit tests.
4. Update docs and examples; rebuild docs.
5. Remove deprecated modules for a clean Hive-only tree.

## Backward-compatibility notes

- Consider one minor release with deprecation warnings before removal.
- Provide migration hints in error messages and docs (e.g., remove `--steem/--blurt` flags; switch to `Hive()` API).

## Acceptance criteria

- No references to "Steem" or "Blurt" in code (except in CHANGELOG/history).
- CLI help and docs show Hive-only options and examples.
- Test suite passes on Hive default chain.

## Per-file Hive-only checklist

Use this checklist to verify each file has been audited and updated (or removed) for Hive-only support. Check off when complete.

### src/

- [x] `src/nectar/__init__.py`
- [x] `src/nectar/account.py`
- [ ] `src/nectar/amount.py`
- [ ] `src/nectar/asciichart.py`
- [ ] `src/nectar/asset.py`
- [ ] `src/nectar/block.py`
- [ ] `src/nectar/blockchain.py`
- [ ] `src/nectar/blockchaininstance.py`
- [ ] `src/nectar/blockchainobject.py`
- [ ] `src/nectar/blurt.py`  (remove or replace)
- [ ] `src/nectar/cli.py`
- [ ] `src/nectar/comment.py`
- [ ] `src/nectar/community.py`
- [ ] `src/nectar/conveyor.py`
- [ ] `src/nectar/constants.py`
- [ ] `src/nectar/discussions.py`
- [ ] `src/nectar/exceptions.py`
- [ ] `src/nectar/hive.py`
- [ ] `src/nectar/hivesigner.py`
- [ ] `src/nectar/imageuploader.py`
- [ ] `src/nectar/instance.py`
- [ ] `src/nectar/market.py`
- [ ] `src/nectar/memo.py`
- [ ] `src/nectar/message.py`
- [ ] `src/nectar/nodelist.py`
- [ ] `src/nectar/price.py`
- [ ] `src/nectar/profile.py`
- [ ] `src/nectar/rc.py`
- [ ] `src/nectar/snapshot.py`
- [ ] `src/nectar/steem.py`  (remove or replace)
- [ ] `src/nectar/transactionbuilder.py`
- [ ] `src/nectar/utils.py`
- [ ] `src/nectar/version.py`
- [ ] `src/nectar/vote.py`
- [ ] `src/nectar/wallet.py`
- [ ] `src/nectar/witness.py`

- [ ] `src/nectarapi/__init__.py`
- [ ] `src/nectarapi/exceptions.py`
- [ ] `src/nectarapi/graphenerpc.py`
- [ ] `src/nectarapi/node.py`
- [ ] `src/nectarapi/noderpc.py`
- [ ] `src/nectarapi/rpcutils.py`
- [ ] `src/nectarapi/version.py`

- [ ] `src/nectarbase/__init__.py`
- [ ] `src/nectarbase/ledgertransactions.py`
- [ ] `src/nectarbase/memo.py`
- [ ] `src/nectarbase/objecttypes.py`
- [ ] `src/nectarbase/objects.py`
- [ ] `src/nectarbase/operationids.py`
- [ ] `src/nectarbase/operations.py`
- [ ] `src/nectarbase/signedtransactions.py`
- [ ] `src/nectarbase/transactions.py`
- [ ] `src/nectarbase/version.py`

- [ ] `src/nectargraphene/__init__.py`

- [ ] `src/nectargraphenebase/__init__.py`
- [ ] `src/nectargraphenebase/account.py`
- [ ] `src/nectargraphenebase/aes.py`
- [ ] `src/nectargraphenebase/base58.py`
- [ ] `src/nectargraphenebase/bip32.py`
- [ ] `src/nectargraphenebase/bip38.py`
- [ ] `src/nectargraphenebase/chains.py`
- [ ] `src/nectargraphenebase/dictionary.py`
- [ ] `src/nectargraphenebase/ecdsasig.py`
- [ ] `src/nectargraphenebase/objecttypes.py`
- [ ] `src/nectargraphenebase/operationids.py`
- [ ] `src/nectargraphenebase/objects.py`
- [ ] `src/nectargraphenebase/operations.py`
- [ ] `src/nectargraphenebase/prefix.py`
- [ ] `src/nectargraphenebase/signedtransactions.py`
- [ ] `src/nectargraphenebase/types.py`
- [ ] `src/nectargraphenebase/unsignedtransactions.py`
- [ ] `src/nectargraphenebase/version.py`

- [ ] `src/nectarstorage/__init__.py`
- [ ] `src/nectarstorage/base.py`
- [ ] `src/nectarstorage/exceptions.py`
- [ ] `src/nectarstorage/interfaces.py`
- [ ] `src/nectarstorage/masterpassword.py`
- [ ] `src/nectarstorage/ram.py`
- [ ] `src/nectarstorage/sqlite.py`

### tests/

- [ ] `tests/__init__.py`
- [ ] `tests/nectar/__init__.py`
- [ ] `tests/nectar/nodes.py`
- [ ] `tests/nectar/test_account.py`
- [ ] `tests/nectar/test_account_blurt.py`  (remove or replace)
- [ ] `tests/nectar/test_account_steem.py`  (remove or replace)
- [ ] `tests/nectar/test_aes.py`
- [ ] `tests/nectar/test_amount.py`
- [ ] `tests/nectar/test_asciichart.py`
- [ ] `tests/nectar/test_asset.py`
- [ ] `tests/nectar/test_base_objects.py`
- [ ] `tests/nectar/test_block.py`
- [ ] `tests/nectar/test_blockchain.py`
- [ ] `tests/nectar/test_blockchain_batch.py`
- [ ] `tests/nectar/test_blockchain_threading.py`
- [ ] `tests/nectar/test_cli.py`
- [ ] `tests/nectar/test_comment.py`
- [ ] `tests/nectar/test_connection.py`
- [ ] `tests/nectar/test_constants.py`
- [ ] `tests/nectar/test_conveyor.py`
- [ ] `tests/nectar/test_discussions.py`
- [ ] `tests/nectar/test_hive.py`
- [ ] `tests/nectar/test_hivesigner.py`
- [ ] `tests/nectar/test_market.py`
- [ ] `tests/nectar/test_memo.py`
- [ ] `tests/nectar/test_nodelist.py`
- [ ] `tests/nectar/test_objectcache.py`
- [ ] `tests/nectar/test_price.py`
- [ ] `tests/nectar/test_profile.py`
- [ ] `tests/nectar/test_steem.py`  (remove or replace)
- [ ] `tests/nectar/test_storage.py`
- [ ] `tests/nectar/test_testnet.py`
- [ ] `tests/nectar/test_txbuffers.py`
- [ ] `tests/nectar/test_vote.py`
- [ ] `tests/nectar/test_wallet.py`
- [ ] `tests/nectar/test_utils.py`

- [ ] `tests/nectarapi/__init__.py`
- [ ] `tests/nectarapi/test_node.py`
- [ ] `tests/nectarapi/test_noderpc.py`
- [ ] `tests/nectarapi/test_rpcutils.py`

- [ ] `tests/nectarbase/__init__.py`
- [ ] `tests/nectarbase/test_ledgertransactions.py`
- [ ] `tests/nectarbase/test_memo.py`
- [ ] `tests/nectarbase/test_objects.py`
- [ ] `tests/nectarbase/test_operations.py`
- [ ] `tests/nectarbase/test_transactions.py`

- [ ] `tests/nectargraphene/__init__.py`
- [ ] `tests/nectargraphene/test_account.py`
- [ ] `tests/nectargraphene/test_base58.py`
- [ ] `tests/nectargraphene/test_bip32.py`
- [ ] `tests/nectargraphene/test_bip38.py`
- [ ] `tests/nectargraphene/test_ecdsa.py`
- [ ] `tests/nectargraphene/test_key_format.py`
- [ ] `tests/nectargraphene/test_objects.py`
- [ ] `tests/nectargraphene/test_py23.py`
- [ ] `tests/nectargraphene/test_types.py`

- [ ] `tests/nectarstorage/__init__.py`
- [ ] `tests/nectarstorage/test_keystorage.py`
- [ ] `tests/nectarstorage/test_masterpassword.py`
- [ ] `tests/nectarstorage/test_sqlite.py`

### examples/

- [x] `examples/account_curation_per_week_and_1k_sp.py`
- [x] `examples/account_rep_over_time.py`
- [x] `examples/account_sp_over_time.py`
- [x] `examples/account_vp_over_time.py`
- [x] `examples/accout_reputation_by_SP.py`
- [x] `examples/benchmark_nectar.py`
- [x] `examples/benchmark_nodes.py`
- [x] `examples/benchmark_nodes2.py`
- [ ] `examples/blockactivity.py`
- [ ] `examples/blockstats.py`
- [x] `examples/cache_performance.py`
- [ ] `examples/check_followers.py`
- [x] `examples/compare_transactions_speed_with_steem.py`  (updated)
- [ ] `examples/compare_with_steem_python_account.py`  (update or remove)
- [x] `examples/hf20_testnet.py`
- [ ] `examples/login_app/app.py`
- [x] `examples/memory_profiler1.py`
- [x] `examples/memory_profiler2.py`
- [ ] `examples/next_witness_block_coundown.py`
- [x] `examples/op_on_testnet.py`
- [ ] `examples/post_to_html.py`
- [ ] `examples/post_to_md.py`
- [x] `examples/print_appbase_calls.py`
- [ ] `examples/print_comments.py`
- [ ] `examples/print_votes.py`
- [x] `examples/stream_threading_performance.py`
- [x] `examples/using_custom_chain.py`
- [x] `examples/using_steem_offline.py`  (updated)
- [ ] `examples/waitForRecharge.py`
- [x] `examples/watching_the_watchers.py`
- [ ] `examples/write_blocks_to_file.py`

## Progress log

- 2025-08-26 11:22:30 -0400: Completed Hive-only cleanup in `src/nectar/account.py`.
  - Removed deprecated SBD wrappers and all STEEM/SBD references.
  - Updated docstrings to HIVE/HBD and fixed minor lints/indentation.
  - Kept API stable for HBD/HIVE paths; ready to add compat shims if needed.

- 2025-08-26 12:10:00 -0400: HiveSigner-only defaults and label cleanup in CLI.
  - `src/nectar/storage.py`: Removed SteemConnect defaults; set HiveSigner `hs_api_url`/`hs_oauth_base_url`; kept `oauth_base_url` as compat alias.
  - `src/nectar/cli.py`: Legacy `sc2_api_url` now maps to `hs_api_url`; setting `oauth_base_url` updates `hs_oauth_base_url`.
  - Ensured posting payout options prefer `percent_hbd`; legacy `--percent-steem-dollars` retained as alias and normalized.
