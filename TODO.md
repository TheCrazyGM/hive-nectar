# Hive-Nectar Refactoring Plan (Phase 1)

This document outlines the step-by-step plan to refactor the `hive-nectar` codebase, removing legacy components, modernizing the code, and aligning it with the `hived-api` specifications.

## I. Project-Wide Modernization

These tasks should be performed across all modules as applicable.

- **[x] Replace `requests` with `httpx`:**
  - Audit all modules for `requests` imports and usage.
  - Replace with asynchronous-capable `httpx` calls.
  - **Affected files:** `nectar/haf.py`, `nectar/hivesigner.py`, `nectar/imageuploader.py`, `nectar/market.py`, `nectarapi/graphenerpc.py`.

- **[x] Enforce Modern Python Standards:**
  - **[x] Type Hinting:** Add or improve type hints for all function signatures and class variables.
  - **[x] f-strings:** Replace all old-style `.format()` calls and `%` formatting with f-strings.
  - **[x] Pathlib:** Use `pathlib.Path` for all file path manipulations.

## II. Configuration (`nectar/storage.py`)

- **[x] Simplify Configuration Defaults:**
  - Remove Hivesigner-related keys: `hs_api_url`, `hs_oauth_base_url`, `oauth_base_url`.
  - Evaluate and remove other unnecessary default settings.

## III. Core Components (`nectar/hive.py`, `nectar/blockchaininstance.py`)

- **[x] Eliminate Hivesigner Integration:**
  - Remove `use_hs` and `hivesigner` parameters from `Hive()` and `BlockChainInstance()` constructors.
  - Delete all logic related to initializing or handling `HiveSigner` objects.

- **[ ] Remove Legacy Instance Kwargs:**
  - Remove the backward-compatibility logic for `steem_instance` and `hive_instance`.
  - The `blockchain_instance` parameter should be the single source for passing a client instance.

## IV. API & RPC Layer (`nectarapi/`, `nectargrapheneapi/`)

- **[x] Assume Appbase API:**
  - **[x]** Remove all `is_appbase_ready()` and `get_use_appbase()` checks.
  - **[x]** Refactor all RPC calls to assume a modern, Appbase-enabled Hive endpoint.
  - **[x]** Delete conditional logic that branches between appbase and legacy API calls.
  - **[x]** **FIXED:** Fixed API endpoint mapping - changed `api="database"` to `api="database_api"` and similar across all modules.
  - **[x]** **FIXED:** Fixed RPC query generation in `rpcutils.py` to properly handle dict arguments for appbase.
  - **[x]** **FIXED:** Fixed httpx request method to use `data` parameter instead of `content`.
  - **Affected files:** `graphenerpc.py`, `rpcutils.py`, and all modules that call them.

- **[x] Remove Legacy Chain Detection:**
  - In `nectarapi/graphenerpc.py`, remove the logic that checks for and deletes `STEEM_CHAIN_ID` from node properties. The library should be Hive-first.

## V. Blockchain Primitives (`nectarbase/`, `nectargraphenebase/`)

- **[x] Clean Up Operations:**
  - In `nectarbase/operations.py`, remove the deprecated `percent_steem_dollars` parameter and its logic. Use `percent_hbd` exclusively.

- **[ ] Preserve Critical Legacy Identifiers (with clarification):**
  - In `nectarbase/objects.py` and `nectarbase/ledgertransactions.py`, ensure that the serialization logic mapping `HIVE` -> `STEEM` and `HBD` -> `SBD` is preserved for cryptographic compatibility.
  - Add prominent comments to these sections explaining *why* this legacy behavior is intentionally kept.
  - The public key prefix `STM` must also be maintained.

## VI. High-Level Abstractions (`nectar/` modules)

This applies to `account.py`, `comment.py`, `discussions.py`, `market.py`, `vote.py`, `witness.py`, etc.

- **[x] Remove Conditional `appbase` Logic:**
  - Strip out all `if self.blockchain.rpc.get_use_appbase():` blocks and assume the `True` path.

- **[x] Remove Legacy `steem_instance` Kwargs:**
  - Clean up all function and class initializers that accept `steem_instance` or `hive_instance` for backward compatibility.

- **[x] Refactor `discussions.py`:**
  - **[PARTIALLY]** The module was partially refactored but still had issues:
  - **[FIXED]** Added missing `observer` parameter to Query class
  - **[FIXED]** Updated bridge API calls to use observer parameter  
  - **[FIXED]** Removed legacy `use_appbase` documentation references
  - **Status**: Core functionality now working, but module could use further cleanup

- **[ ] Refactor `resteem` to `reblog`:**
  - In `nectar/comment.py`, rename the `resteem()` method to `reblog()` to align with modern Hive terminology. Maintain the underlying operation name if it's still `resteem` at the protocol level, but the public-facing method name should change.

## VII. Hivesigner Deprovisioning

- **[x] Delete `nectar/hivesigner.py`:**
  - The entire module is to be removed.

- **[x] Scrub Hivesigner from `TransactionBuilder`:**
  - In `nectar/transactionbuilder.py`, remove all code paths that delegate signing or broadcasting to Hivesigner. The library should only support local (WIF) or Ledger signing.

- **[x] Purge Hivesigner from `CLI`:**
  - **[PARTIALLY]** The `nectar/hivesigner.py` file was deleted, but **58 references** to hivesigner remain in `nectar/cli.py`.
  - **NEEDS WORK:** Remove all command-line arguments, options, and logic related to Hivesigner (`--hivesigner-token`, `--create-hivesigner-link`, etc.).

## VIII. Documentation and Final Review

- **[ ] Update Documentation:**
  - All removed features (Hivesigner, Steem/Blurt support, Appbase flags) must be scrubbed from the documentation (`docs/` directory).
  - Update quickstart guides and examples to reflect the modernized API.

- **[x] Final Audit:**
  - **[FINDINGS]** Performed final search for remaining artifacts:
    - `requests`: ✅ **0 references** (properly replaced with httpx)
    - `steem`: ⚠️ **4 references** (mostly documentation, 1 deprecated `is_steem` method)
    - `blurt`: ⚠️ **1 reference** (likely in dictionary/wordlist)
    - `hivesigner`: ❌ **58 references** (CLI not properly cleaned up)
    - `appbase`: ⚠️ **92 references** (mostly in documentation/comments, logic mostly removed)
  - **[CRITICAL]** The "Assume Appbase API" task was marked as done but had broken RPC connectivity - **FIXED**
  - **[CRITICAL]** The "Purge Hivesigner from CLI" task was marked as done but has 58 remaining references - **NEEDS WORK**
  - **[TESTING]** Core RPC functionality now working after fixing API endpoint mapping