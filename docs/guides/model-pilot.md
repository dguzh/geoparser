# Offline model pilot

The repository includes a small, real-model Andorra pilot for checking the
full recognition and resolution path without bundling checkpoints. It uses
the multilingual `fastino/gliner2.5-multi-v1` recognizer, Jina's
`jinaai/jina-embeddings-v5-text-small` embeddings, and
`jinaai/jina-reranker-v3.5` reranker against the 3,268-feature Andorra
gazetteer fixture.

Provision the checkpoints in an existing Hugging Face cache, then run:

```bash
HF_HOME=/path/to/hf-cache HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  uv run python scripts/pilot.py \
  --config tests/fixtures/gazetteer/andorranames.yaml \
  --output-dir pilot-results \
  --hf-home /path/to/hf-cache --offline
```

The command writes `pilot-report.json` and `pilot-report.md`, plus the
generated gazetteer and a temporary SQLite database, to the output directory.
The JSON preserves every observed span, identifier, model name, and timing;
the Markdown file is a compact human-readable summary.

For a small system volume, keep the Hugging Face cache, output directory, and
temporary directory on a larger volume. The pilot recognizes all documents in
one batch, releases GLiNER before loading Jina, bounds the short-document
context window to 128 tokens, and converts only the CPU reranker to float32.
These choices reduce peak local resource pressure without replacing real
inference with mocks.

## Reading the resolution number

The pilot reports exact-identifier resolution accuracy, and on the committed
run that number is low (1 of 15 gold annotations). Read it with the per-document
table rather than on its own, because it is dominated by a granularity choice
rather than by the resolver finding the wrong place.

GeoNames stores an Andorran parish twice: once as the populated place and once
as the first-order administrative division that shares its name. Of the seven
resolved mismatches on the committed run, five are exactly that pair:

| Gold | Predicted |
| --- | --- |
| `3041563` Andorra la Vella (PPLC) | `3041566` Andorra la Vella (ADM1) |
| `3041204` Canillo (PPLA) | `3041203` Canillo (ADM1) |
| `3039163` Sant Julià de Lòria (PPLA) | `3039162` Sant Julià de Lòria (ADM1) |
| `3040686` Encamp (PPLA) | `3040684` Encamp (ADM1) |
| `3338529` Escaldes-Engordany (ADM1) | `3040051` les Escaldes (PPLA) |

Counting a same-place, different-granularity hit as correct raises accuracy on
this run from 0.067 to 0.400. Only one prediction is a genuinely different
place: `Andorra` in the Spanish sentence resolves to `3039328` Radio Andorra
(a radio station) instead of `3041565` Principality of Andorra.

Both numbers are worth keeping. Exact accuracy is the honest strict metric and
is what the report computes; the breakdown above is what stops it being read as
"the resolver does not work". The remaining gap on this run is four spans that
were recognized but left unresolved and three that were never recognized.

Neither figure is a benchmark. Fifteen annotations over thirteen sentences is a
smoke test for the wiring, not a measurement of model quality.
