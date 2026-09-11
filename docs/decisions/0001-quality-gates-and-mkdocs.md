# ADR 0001: Quality gates and MkDocs

## Status

Accepted — 2026-09-11

## Context

The project needs one reproducible developer workflow and public documentation
that can be built in CI. The previous documentation stack used Sphinx with
theme-specific configuration, while quality checks were split across several
commands and did not consistently enforce architecture or mutation results.

## Decision

Use `uv` and `uv.lock` for dependency reproducibility, Ruff and `ty` for static
quality, pytest plus Hypothesis and pytest-bdd for behavior, an AST-based
architecture check for dependency boundaries, and a single ordered quality
gauntlet for local and CI verification. Migrate the public site to MkDocs
Material and generate API reference pages with mkdocstrings. Keep large data
and model artifacts outside the repository and document provenance before any
Hugging Face publication.

## Tradeoffs

MkDocs has a smaller configuration surface and a simpler Markdown authoring
workflow, but it does not provide Sphinx's full cross-reference system. The
project accepts explicit Markdown links and focused API directives in exchange
for easier local builds and public hosting. Mutation and CRAP checks add
runtime, so they run as explicit gates and keep generated artifacts outside
the source tree.

## Consequences

Documentation links and API directives must be checked by a strict MkDocs
build. New architectural exceptions require a deliberate checker/test update.
The quality gate is the canonical command for acceptance, while individual
commands remain available for fast feedback during TDD.
