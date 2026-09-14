# ADR 0003: Resource-bounded real-model pilot

## Status

Accepted — 2026-09-14

## Context

The project needs executable evidence from the configured recognizer and
resolver checkpoints, but the checkpoints are large and the Mac has a small
system volume. A pilot must therefore be reproducible, inspectable, and safe
to rerun without copying models into the repository or silently downloading
them.

## Decision

Use a fixed 13-document Andorra corpus with hand-written spans, the real
`fastino/gliner2.5-multi-v1`, `jinaai/jina-embeddings-v5-text-small`, and
`jinaai/jina-reranker-v3.5` checkpoints, and the 3,268-feature
`andorranames` fixture. Run the project recognition and resolution services in
two phases, release GLiNER before constructing Jina, batch the short inputs,
limit the resolver context to 128 tokens, and convert only the reranker to
float32 on CPU. Persist JSON and Markdown evidence beside a generated
gazetteer on the caller-selected output volume.

## Tradeoffs

The two-phase run takes longer than keeping both model graphs alive, and the
timing report separates per-document recognition and resolution decisions from
shared batch embedding work. The fixed corpus is not a benchmark of global
geoparser quality; it is a deterministic smoke test that exposes real model
behavior and resolution errors.

## Consequences

Model caches and generated evidence remain external to source control. Offline
mode makes missing checkpoints fail immediately instead of creating an
unbounded download. Any future pilot expansion must update its gold spans and
acceptance evidence rather than silently changing the corpus.
