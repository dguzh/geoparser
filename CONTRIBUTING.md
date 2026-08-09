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

CI runs on pull requests only, never on branch pushes, so a commit is tested once rather than twice. The full matrix is three operating systems across Python 3.10–3.14. Pushing again to an open pull request cancels the previous run.

If you add a dependency, commit the updated `poetry.lock` alongside `pyproject.toml`, and prefer permissively licensed packages — geoparser is MIT-licensed and its dependencies should not impose stricter terms on users.

## Releasing

Releases are driven entirely by tags, and the tag name is the version — there is no release branch. Tags carry no `v` prefix.

**Step 1 — set the version.** The version lives in `pyproject.toml`, so bumping it is an ordinary code change. Set the *final* version even if you plan to cut release candidates first.

**Step 2 — tag the merged commit.** A tag is a separate ref, not a branch push, so the branch ruleset does not apply and this works even though `main` rejects direct pushes:

```bash
git switch main && git pull
git tag 0.6.0rc1 && git push origin 0.6.0rc1
```

**Step 3 — verify the published artifact.** PEP 440 hides pre-releases from resolvers, so `--pre` is required to see it at all and ordinary users cannot install it by accident:

```bash
python -m venv /tmp/rc && /tmp/rc/bin/pip install --pre geoparser==0.6.0rc1
/tmp/rc/bin/python -c "import geoparser; print(geoparser.__version__)"
```

**Step 4 — cut the real release.** No second version bump is needed; a release-candidate tag stamps its own version onto the build, while a plain tag uses the version already in `pyproject.toml`:

```bash
git tag 0.6.0 && git push origin 0.6.0
```

If the candidate needs fixes, merge them through a pull request as usual and tag `0.6.0rc2`.

### What the tag decides

A tag containing `rc` publishes to PyPI as a pre-release, which `pip install geoparser` will not pick up, and leaves nothing on the Releases page. A plain `MAJOR.MINOR.PATCH` tag publishes a full release, signs the artifacts with Sigstore, and creates the GitHub Release.

### The safeguards

Before anything is published, the workflow checks that the tagged commit is reachable from `main`, so a tag accidentally placed on a feature branch is rejected. It then checks the tag against `pyproject.toml` and refuses to publish if they disagree, so tagging `0.7.0` when the file says `0.6.0` fails instead of shipping. A malformed tag such as `v0.6.0` or `0.6` does not match the trigger at all and is silently ignored.

### Tags and GitHub Releases

A tag is a git ref pointing at a commit. A GitHub Release is a page GitHub builds on top of a tag, carrying a title, notes and file attachments. Every release needs a tag; a tag needs no release.

Both directions work, and the workflow handles either:

- **Tag from the command line.** The tag triggers the workflow, which creates the GitHub Release for you with auto-generated notes — for final versions only.
- **Publish a release from the web UI.** Creating the release creates the tag, which triggers the same workflow; it then attaches the signed artifacts to the release you published instead of generating its own. Use this when you want to write the notes by hand. This applies to final versions only — publishing a release for an `rc` tag still uploads to PyPI, but the workflow attaches nothing, so the release page stays empty.

Only *publishing* a release creates its tag. Saving a draft does not, so nothing runs until you press publish.

## Licensing

This project is MIT-licensed; see [LICENSE](./LICENSE). Dependencies are declared rather than bundled, so each one is distributed under its own license by its own maintainers; pip installs those license files alongside the packages.
