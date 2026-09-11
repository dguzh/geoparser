# Development

The repository uses `uv` for environments and locked dependencies, Ruff for
linting and formatting, `ty` for type checking, and pytest for tests.

## Local workflow

```bash
uv sync --locked
uv run ruff format --check .
uv run ruff check .
uv run ty check geoparser scripts tests
uv run pytest
```

The intended development loop is RED → GREEN → REFACTOR: first write a
focused failing test, make the smallest implementation change, then simplify
and review the result. Tests are grouped as unit, integration, property-based,
acceptance, and end-to-end checks where those boundaries provide useful
confidence.

## Quality gauntlet

Run the complete deterministic gate with:

```bash
uv run python scripts/quality_gauntlet.py
```

The command runs the stages in dependency order: baseline, Ruff, `ty`, locked
dependency validation, tests, property tests, acceptance tests, architecture
checks, CRAP, mutation tests, a CLI smoke test, and diff review. Generated
reports belong in a temporary directory and are not committed. The runner also
uses a unique Docker smoke-test tag and removes that image when it exits.

### Resource-safe local gate

Mutation testing can use several gigabytes while it runs. On a machine with a
small system volume, point both temporary files and uv's cache at disposable
directories on a larger volume; create them first:

```bash
mkdir -p /path/on-a-large-volume/geoparser-qa-tmp \
  /path/on-a-large-volume/geoparser-qa-uv-cache
TMPDIR=/path/on-a-large-volume/geoparser-qa-tmp \
UV_CACHE_DIR=/path/on-a-large-volume/geoparser-qa-uv-cache \
uv run --no-sync python scripts/quality_gauntlet.py
```

The runner removes its temporary reports and mutation tree after the command.
The uv cache is reusable; remove that exact cache directory when it is no
longer useful.

## Documentation

Build the public site locally with:

```bash
uv run mkdocs build --strict
```

The site uses MkDocs Material. API pages use `mkdocstrings` directly from the
source package, so public signatures and docstrings remain close to the code.

## Pull requests

Keep changes small and behavior-focused. Add a permanent regression test for
every discovered bug, update an ADR when a design tradeoff changes, and record
known limitations in [Technical Debt](technical-debt.md). CI blocks acceptance
when deterministic quality or architecture gates fail.
