# Data and models

The source repository contains code, small deterministic fixtures, and public
configuration examples. Large gazetteers and model checkpoints are runtime
artifacts: they are downloaded explicitly, cached outside the repository, and
never silently committed.

## Gazetteers

Install a pre-configured gazetteer with the CLI, for example
`python -m geoparser install geonames`. Custom gazetteers are described in the
[custom gazetteers guide](guides/custom-gazetteers.md). The resulting artifact
is a self-contained SQLite file stored in the platform data directory.

## Model checkpoints

The built-in modules fetch their declared checkpoints from their upstream model
registries. The exact model and configuration are part of a module's identity,
so changing either produces a separately identifiable result set. Model
downloads are not required for unit tests; integration tests should use a
fixture or an explicitly provisioned cache.

## Hugging Face provenance

Hugging Face is used as an upstream registry for model checkpoints and may be
used for project-owned datasets or models when a release requires it. Any
future publication must record the repository identifier, revision, license,
schema, and generation command in the release documentation before upload.
This repository currently has no project-owned artifact authorized for an
automatic upload, so the quality gate does not publish data or model files.

## Reproducibility

Prefer locked dependencies, deterministic fixtures, explicit schemas, golden
outputs, and seeded replay. Large external resources should be versioned by
their upstream revision or checksum rather than copied into source control.
