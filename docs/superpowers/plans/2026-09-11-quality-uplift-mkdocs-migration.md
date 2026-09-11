# Repository Quality Uplift and MkDocs Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the public documentation from Sphinx to strict MkDocs Material and make the requested deterministic quality gauntlet executable locally and blocking in CI without changing library behavior.

**Architecture:** Keep `geoparser/` runtime behavior unchanged. Add small, side-effect-isolated quality tools under `scripts/`, test them through stable command contracts, use AST-only architecture checks for dependency cycles and layer violations, and keep generated coverage, mutation, build, and Docker artifacts outside the repository. Convert the existing public documentation into Markdown with a single MkDocs navigation and use `mkdocstrings` only for API surfaces that must follow Python signatures.

**Tech Stack:** uv and `uv.lock`, Ruff, ty, pytest/pytest-cov, Hypothesis, pytest-bdd, radon/CRAP, mutmut, MkDocs Material, mkdocstrings, Python AST, Docker, GitHub Actions, GitHub Pages.

---

### Task 1: Establish the quality-contract tests

**Files:**
- Create: `tests/unit/test_quality/__init__.py`
- Create: `tests/unit/test_quality/test_project_contract.py`
- Modify: `pyproject.toml`

- [ ] **Step 1: Write failing contract tests**

Add tests that inspect `pyproject.toml` with `tomllib`. The first contract slice must require the `hypothesis` and `pytest-bdd` development dependencies and the `property`, `acceptance`, and `architecture` pytest markers. Later tasks extend this same contract test with the files and workflow assertions they introduce.

- [ ] **Step 2: Run the focused tests and capture RED**

Run:

```bash
uv run --no-sync pytest tests/unit/test_quality/test_project_contract.py -q
```

Expected result: failure because the new quality entrypoints, MkDocs configuration, Docker packaging, citation metadata, and dependencies do not yet exist.

- [ ] **Step 3: Implement the minimum project contract**

Add the dependency and marker declarations only. Keep dependency versions bounded and let `uv lock` update the lockfile.

- [ ] **Step 4: Run the focused tests and verify GREEN**

Run the same focused pytest command and require all contract assertions to pass.

- [ ] **Step 5: Commit the contract foundation**

```bash
git add pyproject.toml uv.lock tests/unit/test_quality/test_project_contract.py tests/unit/test_quality/__init__.py
git commit -m "test: define repository quality contracts"
```

### Task 2: Add the architecture and dependency-boundary checker

**Files:**
- Create: `scripts/check_architecture.py`
- Create: `tests/unit/test_quality/test_architecture.py`
- Modify: `pyproject.toml`

- [ ] **Step 1: Write failing tests for the stable checker interface**

Test `build_import_graph`, `find_cycles`, and `find_boundary_violations` against temporary packages. Cover an acyclic graph, a three-node cycle, a runtime forbidden import, and an import under `if TYPE_CHECKING:` that is allowed for annotations. Also test that the real `geoparser` package is checked from the repository root.

- [ ] **Step 2: Run the focused tests and verify RED**

```bash
uv run --no-sync pytest tests/unit/test_quality/test_architecture.py -q
```

Expected result: import failure for the missing script functions.

- [ ] **Step 3: Implement the minimal AST-only checker**

Implement a pure graph builder that maps Python files to module names, resolves internal imports to the nearest real module/package, skips external imports, distinguishes runtime imports from `TYPE_CHECKING` imports, reports deterministic DFS cycles, and enforces these current boundaries:

```python
FORBIDDEN = {
    "geoparser.db": {
        "geoparser.modules",
        "geoparser.services",
        "geoparser.project",
        "geoparser.context",
    },
    "geoparser.modules": {
        "geoparser.db",
        "geoparser.services",
        "geoparser.project",
        "geoparser.context",
    },
    "geoparser.context": {
        "geoparser.modules",
        "geoparser.services",
        "geoparser.project",
    },
    "geoparser.services": {
        "geoparser.modules",
        "geoparser.project",
        "geoparser.context",
    },
}
```

The CLI must accept `--package geoparser`, print cycles and violations in sorted order, return `0` only when both sets are empty, and return `1` otherwise.

- [ ] **Step 4: Run focused tests and the real checker**

```bash
uv run --no-sync pytest tests/unit/test_quality/test_architecture.py -q
uv run --no-sync python scripts/check_architecture.py --package geoparser
```

Both commands must pass with no cycle or boundary violation.

- [ ] **Step 5: Commit the architecture gate**

```bash
git add scripts/check_architecture.py tests/unit/test_quality/test_architecture.py pyproject.toml
git commit -m "feat: enforce import architecture boundaries"
```

### Task 3: Add invariant and acceptance coverage

**Files:**
- Create: `tests/property/__init__.py`
- Create: `tests/property/test_matching_invariants.py`
- Create: `tests/acceptance/__init__.py`
- Create: `tests/acceptance/features/parse_manual.feature`
- Create: `tests/acceptance/test_parse_manual.py`
- Modify: `pyproject.toml`

- [ ] **Step 1: Write property tests before any implementation change**

Use Hypothesis to generate ASCII text containing letters, digits, whitespace, and punctuation. Assert that `soundex` is empty for input with no letters, otherwise has four characters with an alphabetic first character and numeric suffix; assert ASCII case normalization invariance; and assert Levenshtein symmetry, non-negativity, and zero distance for equivalent processed strings.

- [ ] **Step 2: Run property tests and verify they exercise the existing implementation**

```bash
uv run --no-sync pytest tests/property -m property -q
```

Expected result before marker registration: collection/marker failure or missing directory; after adding the test directory and marker, all generated examples must pass without changing runtime code.

- [ ] **Step 3: Write an executable Gherkin scenario**

Create `parse_manual.feature` with a realistic user journey: a caller supplies one text, a manually configured recognizer finds the span for “Zurich”, a manually configured resolver links it to an installed fixture feature, and the parsed document exposes the original text, span, and location identifier.

- [ ] **Step 4: Run the acceptance scenario and verify RED for missing glue**

```bash
uv run --no-sync pytest tests/acceptance -m acceptance -q
```

The initial run must fail at collection until the pytest-bdd dependency, marker, step definitions, and deterministic fixture setup are present.

- [ ] **Step 5: Implement the minimal steps and deterministic fixture**

Use the existing Andorra fixture/database helpers and `ManualRecognizer`/`ManualResolver`; do not download a model or call a network service. Mark the scenario tests with `@pytest.mark.acceptance` and keep all external state behind the existing fixture boundary.

- [ ] **Step 6: Run focused property and acceptance tests GREEN**

```bash
uv run --no-sync pytest tests/property tests/acceptance -m "property or acceptance" -q
```

- [ ] **Step 7: Commit the test-quality additions**

```bash
git add pyproject.toml uv.lock tests/property tests/acceptance
git commit -m "test: add property and acceptance coverage"
```

### Task 4: Migrate the documentation to MkDocs Material

**Files:**
- Create: `mkdocs.yml`
- Create: `docs/index.md`
- Create: `docs/installation.md`
- Create: `docs/quickstart.md`
- Create: `docs/concepts.md`
- Create: `docs/demo.md`
- Create: `docs/guides/annotating.md`
- Create: `docs/guides/custom-gazetteers.md`
- Create: `docs/guides/gazetteers.md`
- Create: `docs/guides/modules.md`
- Create: `docs/guides/projects.md`
- Create: `docs/guides/results.md`
- Create: `docs/guides/training.md`
- Create: `docs/api/gazetteer.md`
- Create: `docs/api/geoparser.md`
- Create: `docs/api/models.md`
- Create: `docs/api/modules.md`
- Create: `docs/api/project.md`
- Create: `docs/architecture.md`
- Create: `docs/development.md`
- Create: `docs/data-and-models.md`
- Create: `docs/technical-debt.md`
- Create: `docs/decisions/0001-quality-gates-and-mkdocs.md`
- Modify: `README.md`
- Modify: `CONTRIBUTING.md`
- Delete: `docs/conf.py`
- Delete: `docs/Makefile`
- Delete: `docs/make.bat`
- Delete: `.readthedocs.yaml`
- Delete: all public `docs/**/*.rst` sources after their Markdown replacements are validated

- [ ] **Step 1: Add a strict MkDocs configuration and build contract**

Configure Material, search, `mkdocstrings`, the existing logo/favicon/CSS assets, `site_url: https://docs.geoparser.app/`, the repository URL discovered from the current remote, `use_directory_urls: false` to preserve `.html`-style links, and an explicit navigation containing every converted page. Configure `mkdocstrings` to document only public classes/functions named in the API pages.

- [ ] **Step 2: Run the strict build to capture RED**

```bash
uv run --no-sync mkdocs build --strict --site-dir /private/tmp/geoparser-mkdocs-site
```

Expected result: missing configuration/dependency or missing pages before the migration is implemented.

- [ ] **Step 3: Convert the public pages**

Translate the existing RST semantics to Markdown: headings, admonitions, tabs, tables, literal includes, cross-links, code fences, and API directives. Keep examples executable and remove only Sphinx syntax. Keep `docs/examples/pleiades.yaml` and existing static assets unchanged unless a Markdown link requires a path adjustment.

- [ ] **Step 4: Add docs validation tests and build GREEN**

Add contract assertions to `tests/unit/test_quality/test_project_contract.py` for `mkdocs.yml` navigation, strict mode compatibility, no `.rst` navigation entries, and required landing-page content. Run the strict build again and inspect that `site/index.html`, every navigation page, search assets, and no private/cache files exist under the output.

- [ ] **Step 5: Update public links and developer instructions**

Point README and contribution links at MkDocs URLs, document `uv run mkdocs build --strict`, and keep the migration/quality rationale in the ADR and technical-debt page.

- [ ] **Step 6: Commit the documentation migration**

```bash
git add mkdocs.yml README.md CONTRIBUTING.md docs
git rm docs/conf.py docs/Makefile docs/make.bat .readthedocs.yaml docs/**/*.rst
git commit -m "docs: migrate public documentation to MkDocs Material"
```

### Task 5: Add reproducible packaging and citation metadata

**Files:**
- Create: `Dockerfile`
- Create: `.dockerignore`
- Create: `CITATION.cff`
- Modify: `README.md`
- Modify: `CONTRIBUTING.md`

- [ ] **Step 1: Add packaging contract tests**

Test that `Dockerfile` copies only `pyproject.toml`/`uv.lock` before dependency installation, installs with `uv sync --locked --no-dev`, exposes no secret or machine-specific path, and has a default scriptable `python -m geoparser --help` command. Test `CITATION.cff` has valid YAML-like CFF fields for version, title, repository-code, license, and one author.

- [ ] **Step 2: Run focused tests and Docker build to verify RED**

```bash
uv run --no-sync pytest tests/unit/test_quality/test_project_contract.py -q
docker build --file Dockerfile --tag geoparser:quality-check .
```

Expected result: the focused assertions/build fail until the files exist.

- [ ] **Step 3: Implement the smallest runtime image**

Use a pinned Python 3.12 slim base compatible with the project range, install uv, copy lock metadata, run `uv sync --locked --no-dev`, copy the package, set `PYTHONUNBUFFERED=1`, and default to `python -m geoparser --help`. Exclude tests, docs sources, caches, local environments, credentials, and generated artifacts through `.dockerignore`.

- [ ] **Step 4: Build and smoke-test GREEN**

```bash
docker build --file Dockerfile --tag geoparser:quality-check .
docker run --rm geoparser:quality-check
```

Require a successful help output and no runtime import error.

- [ ] **Step 5: Commit packaging metadata**

```bash
git add Dockerfile .dockerignore CITATION.cff README.md CONTRIBUTING.md
git commit -m "build: add reproducible Docker packaging"
```

### Task 6: Implement the deterministic quality gauntlet

**Files:**
- Create: `scripts/quality_gauntlet.py`
- Create: `tests/unit/test_quality/test_quality_gauntlet.py`
- Modify: `scripts/crap.py`
- Modify: `CONTRIBUTING.md`

- [ ] **Step 1: Write failing runner tests**

Test that the runner executes named stages in this exact order and stops on the first non-zero exit code: `baseline`, `ruff`, `ty`, `dependencies`, `tests`, `property`, `acceptance`, `architecture`, `crap`, `mutation`, `smoke`, `diff-review`. The `dependencies` stage covers `deptry` and `uv lock --check`; the `smoke` stage covers the package build, strict MkDocs build, and Docker help run. Test that every subprocess receives a bounded temporary artifact directory and that the runner returns the failing command’s exit code.

- [ ] **Step 2: Run focused tests and verify RED**

```bash
uv run --no-sync pytest tests/unit/test_quality/test_quality_gauntlet.py -q
```

Expected result: missing module/function failure.

- [ ] **Step 3: Implement the runner**

Create a small `Stage` dataclass and `run_stage` function using `subprocess.run(..., check=False)` with streamed output. Run the full pytest baseline first, then Ruff check/format, ty, `deptry .`, `uv lock --check`, the full 100% pytest suite, property and acceptance markers, the architecture checker, CRAP with `--max-crap 5.99`, mutmut/export/mutation gate with zero survivors, `uv build` into a temporary directory, strict MkDocs into a temporary directory, Docker build/run, and a final `git diff --check` plus status assertion. Support `--skip-mutation` and `--skip-docker` only for local diagnosis; CI must call the default full sequence.

- [ ] **Step 4: Make CRAP strictly less than six**

Keep the score comparison as `score.crap > args.max_crap` and call it with `5.99`; report the exact worst score and number of functions. Do not weaken coverage or exclude runtime code beyond the existing annotator policy.

- [ ] **Step 5: Run the runner’s focused tests and a short diagnostic invocation**

```bash
uv run --no-sync pytest tests/unit/test_quality/test_quality_gauntlet.py -q
uv run --no-sync python scripts/quality_gauntlet.py --help
```

- [ ] **Step 6: Commit the executable gauntlet**

```bash
git add scripts/quality_gauntlet.py scripts/crap.py tests/unit/test_quality/test_quality_gauntlet.py CONTRIBUTING.md
git commit -m "ci: add deterministic repository quality gauntlet"
```

### Task 7: Make CI enforce the complete contract

**Files:**
- Create: `.github/workflows/docs.yml`
- Modify: `.github/workflows/quality.yml`
- Modify: `.github/workflows/test.yml`
- Modify: `.github/workflows/lint.yml`
- Modify: `CONTRIBUTING.md`

- [ ] **Step 1: Write workflow contract tests**

Extend `tests/unit/test_quality/test_project_contract.py` to parse YAML with the existing PyYAML dependency and require pull-request triggers, the quality gauntlet command, architecture and mutation stages, strict MkDocs, Pages permissions, and a final required-status job. Assert that all merge-path quality jobs run on pull requests and fail closed on failure/cancellation/skips.

- [ ] **Step 2: Run the workflow contract tests and capture RED**

```bash
uv run --no-sync pytest tests/unit/test_quality/test_project_contract.py -q
```

- [ ] **Step 3: Implement CI changes**

Add the `quality-gauntlet` job to the PR path with locked uv setup and a single call to `uv run --no-sync python scripts/quality_gauntlet.py`. Keep the existing matrix coverage job if it remains useful, but make the final status job depend on lint, tests, quality, architecture, and docs. Add `docs.yml` with least-privilege Pages build/deploy permissions and strict `mkdocs build`; use immutable action SHAs where repository policy permits and retain version comments.

- [ ] **Step 4: Run workflow contract tests GREEN and validate YAML syntax**

```bash
uv run --no-sync pytest tests/unit/test_quality/test_project_contract.py -q
uv run --no-sync python -c "import pathlib, yaml; [yaml.safe_load(p.read_text()) for p in pathlib.Path('.github/workflows').glob('*.yml')]; print('workflow YAML valid')"
```

- [ ] **Step 5: Commit CI enforcement**

```bash
git add .github/workflows CONTRIBUTING.md tests/unit/test_quality/test_project_contract.py
git commit -m "ci: enforce quality and documentation gates"
```

### Task 8: Final deterministic QA gauntlet and handoff

**Files:**
- Modify only files required by failed verification.

- [ ] **Step 1: Run the full gauntlet from a clean checkout state**

```bash
uv sync --locked
uv run --no-sync python scripts/quality_gauntlet.py
```

Require, in order: baseline tests, Ruff, ty, full tests, property tests, acceptance tests, architecture checks, CRAP `< 6`, complete mutation stats with zero survivors/timeout/suspicious/segfault statuses, package build, Docker help smoke, strict MkDocs build, and clean diff review.

- [ ] **Step 2: Repair only discovered regressions with RED → GREEN → REFACTOR**

For every failure, add a permanent focused regression test first, reproduce the failure, make the smallest fix, rerun the focused gate, then rerun the full gauntlet. Do not change thresholds to make a failure disappear.

- [ ] **Step 3: Inspect the final diff and generated output**

```bash
git diff --check
git status --short --branch
git diff --stat HEAD~1
```

Review source, tests, docs, workflows, lockfile, Docker context, and citation metadata for unrelated changes, secrets, machine-specific paths, dead files, or stale Sphinx references.

- [ ] **Step 4: Verify repository synchronization and clean temporary artifacts**

Remove only the exact temporary directories created by the gauntlet, verify they are absent, confirm local `HEAD` equals `origin/main`, and leave the worktree clean.

- [ ] **Step 5: Commit any final fixes and report evidence**

Use a Conventional Commit, rerun the affected gates after the commit, and report exact test, coverage, CRAP, mutation, documentation, Docker, architecture, and remote-verification results. Do not claim Hugging Face publication unless an owned artifact and successful remote upload were actually verified.
