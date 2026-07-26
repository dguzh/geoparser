# Contributing

Thanks for contributing to Irchel Geoparser. For product usage, see the [documentation](https://docs.geoparser.app). This file covers local development and the checks that run in CI.

## Setup

This project uses [Poetry](https://python-poetry.org/docs/) for dependency management. Install Poetry, then from the repository root:

```bash
poetry install
```

That creates a virtual environment and installs runtime and development dependencies (including spaCy models used in tests).

Run tools through Poetry:

```bash
poetry run <command>
```

To activate the environment in your current shell instead:

```bash
eval $(poetry env activate)
```

Supported Python versions are `>=3.10,<3.15`. Keep changes compatible across that range.

## Code style

Formatting and import hygiene are checked in CI on every push and pull request; the jobs fail if the code is not clean. Before opening a PR, run:

```bash
poetry run black .
poetry run isort .
poetry run autoflake --remove-all-unused-imports --in-place --recursive --exclude=__init__.py geoparser tests
```

- **black** formats the code (`required-version` is pinned in `pyproject.toml`)
- **isort** sorts imports (`profile = "black"`)
- **autoflake** removes unused imports (`__init__.py` is excluded)

## Tests

Tests live under `tests/` and are organized as:

- `tests/unit/` — fast, isolated tests (usually mocked)
- `tests/integration/` — exercises real components together (models, DB, gazetteers)
- `tests/e2e/` — full pipeline tests

Markers `unit`, `integration`, and `e2e` are defined in `tests/pytest.ini`.

Run the full suite:

```bash
poetry run pytest
```

Coverage is collected for `geoparser` (HTML report in `htmlcov/`; open `htmlcov/index.html`). `geoparser/annotator/` is omitted from coverage. Pull requests expect near-complete coverage of the measured package, so new functionality should ship with tests.

Useful subsets:

```bash
poetry run pytest tests/unit
poetry run pytest tests/integration/test_geoparser_integration.py
```

## Documentation

User-facing docs are Sphinx sources in `docs/` and are published via Read the Docs. After `poetry install`, build them locally with:

```bash
cd docs
poetry run sphinx-build -b html . _build/html
```

Open `docs/_build/html/index.html` in a browser. When you change public APIs or behavior, update the corresponding guides or API pages under `docs/`.

## CLI

The package CLI is available as:

```bash
poetry run python -m geoparser --help
```

Common commands include gazetteer `install` / `list` / `uninstall` and launching the annotator.

## Pull requests

If you want to contribute code, feel free to open a pull request. Issues are also welcome for questions, support, bug reports, or discussing an idea before you start.

A few practical tips that make reviews easier:

- Run black, isort, autoflake, and pytest locally before submitting
- Add or update tests when behavior changes
- Update docs when user-facing behavior changes

Packaging and publishing (build, TestPyPI, PyPI) are handled by GitHub Actions on `staging` / `main` and on tags.

## Licensing

This project is MIT-licensed; see [LICENSE](./LICENSE). Third-party dependency licenses are listed in [THIRD_PARTY_LICENSES](./THIRD_PARTY_LICENSES).
