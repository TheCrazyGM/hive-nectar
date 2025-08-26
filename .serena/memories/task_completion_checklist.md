# Task Completion Checklist

When you finish a change, do the following before opening a PR or committing:

- __Run linters/formatters__
  - uv run ruff check src
  - uv run ruff format src
  - uv run ruff check --select I --fix src  # organize imports

- __Run tests__
  - pytest -v
  - Consider `pytest -k <subset>` for focused runs during iteration

- __Build docs (when touching API/CLI)__
  - make docs
  - Verify for warnings/errors and skim changed pages

- __Build & install locally__
  - make build
  - uv pip install -e .

- __Versioning & changelog__
  - Update `CHANGELOG.md` and bump version in `pyproject.toml` when appropriate

- __CI/Publishing (maintainers)__
  - make release (or `make dist` for packaging)

- __General sanity__
  - grep -R TODO/FIXME around your changes
  - ensure type hints compile if touched (mypy optional)