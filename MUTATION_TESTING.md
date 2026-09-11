# Mutation testing status

A living record of the campaign to leave no surviving mutant. Update the
numbers and the checklist below whenever you work on it.

## How to run it

```bash
uv run mutmut run                 # full sweep, regenerates mutants/
uv run mutmut export-cicd-stats
uv run python scripts/mutation_gate.py --max-survivors <baseline>
```

Inspect one function's survivors with `uv run mutmut results` and
`uv run mutmut show <mutant>`. A targeted re-check after writing a test is
`uv run mutmut run <mutant-name>`, which is seconds rather than minutes.

Pragmas only take effect when the mutant tree is regenerated, so delete
`mutants/` before a run that is meant to pick them up.

## Where the numbers stand

| Run | Mutants | Killed | Survived | No tests | Segfault | Rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Baseline, whole package | 3871 | 2480 | 931 | 290 | 164 | 9.7/s |
| After excluding the build pipeline | 2021 | 1427 | 307 | 286 | 0 | 34.0/s |
| Clean sweep after model pass | 1999 | 1787 | **0** | 212 | 0 | 25.1/s |

`MAX_SURVIVING_MUTANTS` in `.github/workflows/quality.yml` is now `0`.
Keep it at zero: a new survivor is a line the unit suite runs but does not
check.

## Scope, and why

Two exclusions, both measured rather than assumed:

- **`geoparser/annotator/*` and `geoparser/cli/*`** — the annotator is a
  server-rendered UI that coverage also omits, and the CLI is argument wiring
  around code that is mutated on its own.
- **`geoparser/gazetteer/build/*`** — the build pipeline assembles SQL and
  drives duckdb, which the unit suite mocks away. Judging its mutants honestly
  needs the integration suite, and that rebuilds a real gazetteer per mutant:
  about 23 seconds each, some thirteen hours for the package. Excluding it also
  removed every segfault, since those all came from mutating native-extension
  code that mutmut runs in-process. It is covered instead by the integration
  and e2e suites and by the 100% coverage gate.

Mutants are judged by `tests/unit` only. Adding `tests/integration` was tried:
it removes every "no tests" mutant and cuts survival from 29% to about 11%, but
at the cost above.

## Tests or pragma?

A surviving mutant is one of two things, and the distinction is worth keeping
honest:

1. **A real gap.** The suite runs the line but never checks what it did. Write
   the assertion. This is the valuable half.
2. **An equivalent mutant.** Nothing can distinguish it from the original, so
   no test can ever kill it. Mark it `# pragma: no mutate` *with a comment
   saying why*, and prefer evidence over intuition — the two soundex ones were
   confirmed identical over 44,000 random inputs before being marked.

Message wording counts as the second kind. Pinning the prose of an error
word-for-word breaks on every copy-edit while verifying nothing; assert the
part that matters (that the message names the offending file, say) and use an
explicit `start`/`end` pragma region around the `raise`.

A blanket regex over "lines that look like message text" was considered and
rejected: a regex should not be the thing deciding what counts as behaviour.

## Done

Each of these is at zero survivors.

- [x] `SentenceTransformerResolver._expand_window` — 32 (31 tests, 1 pragma)
- [x] `_check_database_compatibility` — 25 (7 tests, 18 pragma: message prose,
      plus SQL keywords and a SQLite identifier, all case-insensitive)
- [x] `SpacyRecognizer` — 20 (19 tests, 1 pragma: download progress message)
- [x] `ResolutionService.fit` / `_annotated_pairs` — 15 (tests)
- [x] `_search_tier`, `_all_resolved`, `_unresolved_candidate_lists`,
      `_merge_candidates`, `_evaluate_document`, `_gather_candidates`,
      `predict` tiers, `_search_once` — tests
- [x] `_encode` — 9 (1 test, 2 pragma: batch size and progress bar are
      throughput and display, not behaviour)
- [x] `soundex` — 9 (7 tests against published reference codes, 2 pragma,
      both verified equivalent empirically)
- [x] `Project._normalize_document_ids`, `create_documents`,
      `_ensure_project_record` — tests, plus 1 pragma for guidance wording
- [x] `gazetteers_dir`, `artifact_path`, `list_artifacts`,
      `register_functions` — tests, plus 1 pragma for the Windows-only
      appauthor argument
- [x] `Project.load_annotations` — 14 (tests: the import's data flow)
- [x] `Project.run_recognizer` / `run_resolver` / `get_documents` — 18 (tests:
      default and explicit tags, and the documents each service receives)
- [x] `_best_referent`, `_token_limit`, `_extract_contexts` — 12 (tests, plus
      1 pragma for the no-maximum-length message wording)
- [x] `RecognitionService._record_reference_predictions` and
      `ResolutionService._record_referent_predictions` — tests for the lenient
      handling of short prediction lists and of None predictions
- [x] `SentenceTransformerResolver._prepare_training_data` — 15 (tests for the
      contrastive pairs: labels, contexts and the gazetteer lookups)
- [x] `ReferenceRepository.update` / `get_by_document_and_span` — 8 (tests for
      the span fallbacks; a redundant `hasattr` guard was deleted rather than
      tested, since the foreign key makes a dangling document impossible)
- [x] `Project._normalize_document_ids` — 5 (1 pragma: guidance wording)

## Current status

The clean sweep after the model pass generated 1,999 mutants and reported:

- **1,787 killed**
- **0 survived**
- **0 timeouts, suspicious results, or segfaults**
- **212 with no covering unit test**

The one transient timeout from the sweep was rerun in isolation and killed;
the final exported stats report zero timeouts. There are no remaining
survivors to investigate.

The 212 no-test mutants are an intentional scope boundary: the mutation run
uses `tests/unit`, while the integration and e2e suites plus the 100% coverage
gate cover the paths that the unit suite does not reach. They remain visible in
the exported stats but are not survivors. No `MAX_NO_TESTS` ratchet is used,
because this count describes the established test-scope split rather than an
unbounded survival budget.
