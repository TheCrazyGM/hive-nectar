# Project Overview

- __Purpose__: `hive-nectar` is a Python library and CLI for interacting with the Hive blockchain. It is a highly opinionated fork of beem with expanded tests, docs, and hivesigner integration.
- __Entry points__:
  - Library packages under `src/` (e.g., `src/nectar/`)
  - CLI script `hive-nectar` -> `nectar.cli:cli` (defined in `pyproject.toml`)
- __Docs__: Sphinx docs in `docs/` (published to ReadTheDocs)
- __Status__: Actively developed; version set in `pyproject.toml`. See `CHANGELOG.md`.
- __Python version__: pyproject requires Python >=3.10; README mentions minimal working 3.12.

# Tech Stack

- __Language__: Python 3.10+
- __CLI__: `click`, `click_shell`, `prettytable`
- __Networking__: `requests`, `websocket-client`
- __Crypto__: `ecdsa`, `pycryptodomex`, `scrypt`
- __Config/IO__: `ruamel.yaml`, `diff_match_patch`, `asn1crypto`
- __Tooling__: `uv` (package/build), `ruff` (lint/format), `pytest`, `sphinx`

# Key Files/Dirs

- `src/nectar/`: core Hive client, CLI, blockchain abstractions
- `src/nectarapi/`, `src/nectarbase/`, `src/nectargraphenebase/`, `src/nectargrapheneapi/`, `src/nectarstorage/`: supporting APIs, base classes, graphene bindings, and storage
- `tests/`: unit tests grouped by package
- `docs/`: documentation sources and build config
- `pyproject.toml`: project metadata, deps, ruff, pytest config
- `Makefile`: common dev tasks (lint, format, test, build, publish)

# Notable Features

- Hivesigner integration
- Works read-only (offline) mode
- Rich blockchain object cache, broadcast ops, and NodeRPC for custom calls