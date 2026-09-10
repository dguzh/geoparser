# Contributing

Thanks for contributing to Irchel Geoparser. For product usage, see the [documentation](https://docs.geoparser.app). This file covers local development and the checks that run in CI.

## Setup

This project uses [uv](https://docs.astral.sh/uv/) for dependency management. Install uv, then from the repository root:

```bash
uv sync
```

That creates `.venv/`, installs runtime and development dependencies (including the spaCy models used in tests) at the versions pinned in `uv.lock`, and installs geoparser itself in editable mode. uv downloads a suitable interpreter automatically, so no separate Python install is needed.

Run tools through uv:

```bash
uv run <command>
```

To activate the environment in your current shell instead:

```bash
source .venv/bin/activate
```

Supported Python versions are `>=3.10,<3.15`. Keep changes compatible across that range.

## Code style

[Ruff](https://docs.astral.sh/ruff/) handles formatting, import sorting, unused-code removal and linting in one tool; it replaces the former black + isort + autoflake trio. Its version is pinned in `pyproject.toml` and locked in `uv.lock`, so CI and your machine format identically.

```bash
uv run ruff check --fix .
uv run ruff format .
```

CI runs the checking form of both and fails if anything is unformatted or unclean:

```bash
uv run ruff check .
uv run ruff format --check .
```

The enabled rule sets are declared under `[tool.ruff.lint]` in `pyproject.toml`. Prefer fixing a finding over silencing it; a `# noqa` needs a specific code and a reason.

## Tests

Tests live under `tests/` and are organized as:

- `tests/unit/` — fast, isolated tests (usually mocked)
- `tests/integration/` — exercises real components together (models, DB, gazetteers)
- `tests/e2e/` — full pipeline tests

Markers `unit`, `integration`, and `e2e` are declared under `[tool.pytest.ini_options]` in `pyproject.toml`, which is the single source of pytest configuration.

Run the full suite:

```bash
uv run pytest
```

Coverage is collected for `geoparser` (HTML report in `htmlcov/`; open `htmlcov/index.html`). `geoparser/annotator/` is omitted from coverage. CI enforces a hard floor on the combined coverage of the whole matrix:

```bash
uv run pytest --cov-fail-under=100
```

The suite is kept fast on purpose. Two things matter if you are adding to it:

- **Do not import the heavy stack at module scope in `geoparser/cli/` or in a
  package `__init__`.** The CLI resolves spaCy, torch and the build pipeline
  per command, which is what keeps `python -m geoparser --help` at a fraction
  of a second instead of the ~9s it used to take. A test pins this.
- Coverage is measured with the `sys.monitoring` core (`core = "sysmon"`),
  which costs under 1% rather than the tracer's overhead. It falls back
  automatically on Python 3.10 and 3.11.

`pytest-xdist` was measured and deliberately not adopted: worker start-up
dwarfs 638 fast unit tests (three times slower), and on the full suite it
moved the wall clock by under 2% for ~80% more CPU.

Useful subsets:

```bash
uv run pytest tests/unit
uv run pytest tests/integration/test_geoparser_integration.py
```

## Quality checks

One sequence reproduces everything CI enforces. Run it from the repository root before opening a pull request:

```bash
uv sync
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run pytest --cov-fail-under=100
uv run python scripts/crap.py --max-crap 6
uv run mutmut run
uv run mutmut export-cicd-stats
uv run python scripts/mutation_gate.py --max-survivors 931
```

What each step guards:

- **ruff check / ruff format** — lint, import order, unused code and formatting.
- **[ty](https://github.com/astral-sh/ty)** — static type checking of `geoparser/`. Fix the type error rather than adding a blanket `# type: ignore`; where a suppression is genuinely right, make it specific and comment why.
- **pytest** — the unit, integration and end-to-end suites, with the hard coverage floor.
- **scripts/crap.py** — the [CRAP score](https://testing.googleblog.com/2011/02/this-code-is-crap.html) gate, `complexity² × (1 − coverage)³ + complexity`, per function. For fully covered code this reduces to a cyclomatic-complexity ceiling, so it fails both on untested code and on code that has grown too branchy. It reads the coverage data that pytest just wrote, so run it after the suite.
- **[mutmut](https://mutmut.readthedocs.io/)** — mutation testing. It edits the source in small ways and re-runs the tests; a mutant that survives is a line the suite does not really check. Configuration lives under `[tool.mutmut]` in `pyproject.toml`; `scripts/mutation_gate.py` reads the exported stats and fails when more mutants survive than the agreed baseline.

Mutation testing runs the library's 3871 mutants against the **unit** suite, at about 9.7 mutants/second once the one-off pass that maps tests to code has finished.

The baseline on this tree is **2480 killed, 931 survived, 290 with no covering unit test — a 72.7% mutation score**. That gap against 100% line coverage is the point of the exercise: a surviving mutant is a line the fast suite executes but never checks. `MAX_SURVIVING_MUTANTS` in `.github/workflows/quality.yml` is a ratchet: lower it as survivors are killed, never raise it.

Judging mutants with the integration suite as well was measured and rejected. It is genuinely more thorough — every `no tests` mutant disappears and survival falls from 29% to about 11% — but each mutant it reaches then rebuilds a real gazetteer, roughly 23 seconds apiece and some thirteen hours for the package. The build pipeline is covered by the integration and e2e suites and by the 100% coverage gate instead. If you want the thorough run, add `"tests/integration"` to `pytest_add_cli_args_test_selection` and set aside an evening.

Around 164 mutants end in a segfault rather than a verdict. They sit in code that calls native extensions (duckdb, threads), which mutmut runs in-process; they are neither killed nor survived, so they are a known blind spot rather than a passing grade.

Inspect survivors with:

```bash
uv run mutmut results
uv run mutmut show <id>
```

A surviving mutant is normally fixed by strengthening a test, not by deleting the mutant.

## Documentation

User-facing docs are Sphinx sources in `docs/` and are published via Read the Docs. After `uv sync`, build them locally with:

```bash
uv run sphinx-build -b html docs docs/_build/html
```

Open `docs/_build/html/index.html` in a browser. When you change public APIs or behavior, update the corresponding guides or API pages under `docs/`.

## CLI

The package CLI is available as:

```bash
uv run python -m geoparser --help
```

Common commands include gazetteer `install` / `list` / `uninstall` and launching the annotator.

## Branches and pull requests

`main` is the only long-lived branch. Work happens on feature branches cut from `main` and comes back through a pull request; direct pushes to `main` are rejected.

If you want to contribute code, feel free to open a pull request. Issues are also welcome for questions, support, bug reports, or discussing an idea before you start.

A few practical tips that make reviews easier:

- Run the local check sequence below before submitting
- Add or update tests when behavior changes
- Update docs when user-facing behavior changes

CI runs on pull requests into `main` and on `main` itself, never on feature-branch pushes. The matrix is three operating systems across Python 3.10–3.14, with uv providing the interpreter on all of them. Pushing again to an open pull request cancels the previous run.

Three workflows run: **Lint** (Ruff, seconds, no project dependencies), **Tests** (the matrix, then the combined coverage and CRAP gates), and **Quality** (ty on every pull request; mutation testing nightly and on demand). Mutation testing is deliberately not a merge gate -- a cold run spends around forty minutes mapping tests to code before it mutates anything -- so the pull request path stays at ruff, ty, tests, coverage and CRAP, which finish in minutes. `tests-passed` is the check the branch ruleset requires; adding the Lint and Quality jobs to that ruleset is a repository setting, not something this file controls.

If you add a dependency, commit the updated `uv.lock` alongside `pyproject.toml` (`uv add <package>` updates both). Prefer permissively licensed packages; geoparser is MIT-licensed.

## Releasing

For maintainers. Releases are driven by tags: the tag name is the version, tags carry no `v` prefix, and there is no release branch.

Bump the version with `uv version <version>` in the last pull request of the cycle, setting the final version even when release candidates come first. Once it is merged, tag from `main`:

```bash
git switch main && git pull
VERSION=$(uv version --short)
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
