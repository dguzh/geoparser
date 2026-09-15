# Technical debt

Known limitations are documented here instead of hidden behind quality
metrics. Each item has a reason and a cleanup direction.

## Database migration support

The database schema is not yet stable across releases, and there is no
automatic migration. Upgrading may require exporting results and recreating
the local database. The intended cleanup path is a versioned migration layer
with fixture-backed upgrade tests before the project reaches 1.0.

## Model and gazetteer availability

Some integration paths require large third-party model checkpoints or
gazetteers. They are intentionally not bundled with the package because of
size, licensing, and update cadence. The cleanup path is a documented,
versioned fixture/cache contract for CI and a small offline test artifact for
each supported module family.

## Annotator boundary

The annotator is a standalone tool with its own database and an import/export
boundary. It predates the current project architecture and may be replaced.
The cleanup path is to stabilize the JSON interchange schema first, then
decide whether the UI should be integrated or retired.

## Public API evolution

The package remains below 1.0, so minor releases may contain breaking changes.
The cleanup path is to treat the API reference and acceptance scenarios as the
compatibility contract, then adopt explicit deprecation periods as the API
settles.

## Mutation coverage scope

Mutation testing deliberately judges the unit-test surface. Gazetteer build
mutants and the server-rendered annotator are covered by integration, end-to-end,
or coverage gates instead because mutating them with full fixtures is currently
too expensive. The cleanup path is to add small deterministic mutation fixtures
for those boundaries, then widen the mutation selection without turning the
quality gate into an unbounded run. The current scope and counts are tracked in
[`MUTATION_TESTING.md`](https://github.com/dguzh/geoparser/blob/main/MUTATION_TESTING.md).
