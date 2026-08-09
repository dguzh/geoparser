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

Formatting and import hygiene are checked in CI on every pull request; the job fails if the code is not clean. Before opening a PR, run:

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

## Branches and pull requests

`main` is the only long-lived branch. Work happens on feature branches cut from `main` and comes back through a pull request; direct pushes to `main` are rejected.

If you want to contribute code, feel free to open a pull request. Issues are also welcome for questions, support, bug reports, or discussing an idea before you start.

A few practical tips that make reviews easier:

- Run black, isort, autoflake, and pytest locally before submitting
- Add or update tests when behavior changes
- Update docs when user-facing behavior changes

CI runs on pull requests into `main` and on `main` itself, never on feature-branch pushes. The matrix is three operating systems across Python 3.10–3.14. Pushing again to an open pull request cancels the previous run.

If you add a dependency, commit the updated `poetry.lock` alongside `pyproject.toml`. Prefer permissively licensed packages; geoparser is MIT-licensed.

## Releasing

For maintainers. Releases are driven by tags: the tag name is the version, tags carry no `v` prefix, and there is no release branch.

Bump the version with `poetry version <version>` in the last pull request of the cycle, setting the final version even when release candidates come first. Once it is merged, tag from `main`:

```bash
git switch main && git pull
VERSION=$(poetry version --short)
git tag "${VERSION}rc1" && git push origin "${VERSION}rc1"
```

Check the candidate in a clean environment. `--pre` is required, since pre-releases are hidden from resolvers:

```bash
python -m venv /tmp/rc
/tmp/rc/bin/pip install --pre "geoparser==${VERSION}rc1"
/tmp/rc/bin/python -c "from importlib.metadata import version; print(version('geoparser'))"
```

Then tag the release itself. No second version bump is needed:

```bash
git tag "$VERSION" && git push origin "$VERSION"
```

If the candidate needs fixes, merge them through a pull request and tag `${VERSION}rc2`.

### What each tag produces

| Tag | PyPI | GitHub Release | Read the Docs |
| --- | --- | --- | --- |
| `1.4.0rc1` | pre-release, needs `--pre` | none | inactive until activated |
| `1.4.0` | release | created, Sigstore-signed | eligible for `stable` |

A final release can also be published from the GitHub web UI when the notes are worth writing by hand. That creates the tag and triggers the same workflow, which attaches the signed artifacts to it. Only publishing creates the tag; saving a draft does not.

### If a tag publishes nothing

- The tag must point at a commit on `main`.
- The tag must agree with `pyproject.toml`, ignoring any `rc` suffix. With the file at `1.4.0`, both `1.4.0` and `1.4.0rc2` are accepted; `1.4.1`, `1.5.0` and `1.5.0rc1` are rejected.
- The tag must read `MAJOR.MINOR.PATCH` or `MAJOR.MINOR.PATCHrcN`. Anything else, such as `v1.4.0`, `1.4` or `1.4.0-rc1`, starts no workflow at all, so there is no failed run to inspect.

## Licensing

This project is MIT-licensed; see [LICENSE](./LICENSE). Dependencies are declared rather than bundled, so each is distributed under its own license by its own maintainers.
