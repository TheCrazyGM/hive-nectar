# Suggested Commands (Linux)

- __Environment setup__
  - uv sync --dev
  - uv pip check

- __Run tests__
  - pytest -v
  - python3 -m pytest -v

- __Lint & format (Ruff)__
  - uv run ruff check src
  - uv run ruff format src
  - uv run ruff check --select I --fix src  # fix imports

- __Build & install__
  - make build
  - uv build
  - uv pip install -e .

- __Docs__
  - make docs  # sphinx-apidoc + html build

- __Release helpers__
  - make generate-versions
  - make tag
  - make dist
  - make release

- __General Git/Linux utils__
  - git status; git diff; git log -n 20
  - ls -la; grep -R "pattern" -n src; find src -name "*.py"

- __CLI entrypoint__
  - hive-nectar  # launches the click shell CLI
