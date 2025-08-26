# Code Style and Conventions

- __Python version__: target Python 3.10+ (tooling supports up to 3.13)
- __Formatting/Linting__: Ruff
  - Line length: 100
  - Quote style: double
  - Indent style: space
  - Lint select: E, F, W, I (pycodestyle/pyflakes/imports)
  - Ignore: E501 (line length)
  - Per-file ignores: `__init__.py` (E402), and `**/{tests,docs,tools}/*` (E402)
- __Imports__: Use Ruff import sorter; run `uv run ruff check --select I --fix src`
- __Type hints__: Gradually adding modern typing (per project work-in-progress)
  - mypy config present but permissive (no disallow_untyped); aim to increase coverage over time
- __Docstrings__: Sphinx-compatible docstrings preferred for API docs; docs generated via `sphinx-apidoc`
- __Testing__: pytest with doctest modules enabled
  - `pytest.ini` sets `addopts = -rw --doctest-modules`
- __CLI UX__: Click-based shell (`nectar.cli:cli`), cohesive help text, consistent option names
- __Directory layout__: src/ layout with typed marker `py.typed` for PEP 561

# Design Guidelines

- Prefer Hive-first abstractions and keep multi-chain code minimal (moving to Hive-only per TODO plan)
- Keep network I/O behind well-defined RPC/instance layers
- Maintain clear separation of concerns across `nectar/`, `nectarapi/`, `nectarbase/`, and graphene bindings
- Ensure functions have deterministic behavior in offline mode where applicable
