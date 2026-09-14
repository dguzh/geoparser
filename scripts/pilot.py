"""Run a real, reproducible Andorra geoparsing pilot and write its evidence."""

from __future__ import annotations

import argparse
import gc
import json
import os
import time
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from geoparser.evaluation import Annotation

Report = dict[str, Any]


@dataclass(frozen=True, slots=True)
class PilotSpan:
    """A hand-written gold span for one pilot document."""

    start: int
    end: int
    identifier: str


@dataclass(frozen=True, slots=True)
class PilotCase:
    """One fixed pilot document and its gold Andorra annotations."""

    case_id: str
    text: str
    gold: tuple[PilotSpan, ...]


ANDORRA_ATTRIBUTE_MAP = {
    "name": "name",
    "type": "feature_name",
    "level1": "country_name",
    "level2": "admin1_name",
    "level3": "admin2_name",
}

# The fixed pilot sentences are all far shorter than this. Bounding the
# encoder window avoids paying for the checkpoint's 8K-token maximum on a
# memory-constrained laptop while preserving every token in this fixture.
MAX_SEQUENCE_LENGTH = 128

PILOT_CASES = (
    PilotCase(
        "capital",
        "Visitors gather in Andorra la Vella.",
        (PilotSpan(19, 35, "3041563"),),
    ),
    PilotCase(
        "encamp",
        "Encamp welcomes hikers in every season.",
        (PilotSpan(0, 6, "3040686"),),
    ),
    PilotCase(
        "canillo",
        "Canillo lies beneath the northern peaks.",
        (PilotSpan(0, 7, "3041204"),),
    ),
    PilotCase(
        "escaldes-engordany",
        "Escaldes-Engordany hosts a thermal spa.",
        (PilotSpan(0, 18, "3338529"),),
    ),
    PilotCase(
        "ordino",
        "Ordino keeps its mountain paths quiet.",
        (PilotSpan(0, 6, "3039678"),),
    ),
    PilotCase(
        "la-massana",
        "La Massana connects the western valleys.",
        (PilotSpan(0, 10, "3040132"),),
    ),
    PilotCase(
        "sant-julia-de-loria",
        "Sant Julià de Lòria marks the southern route.",
        (PilotSpan(0, 19, "3039163"),),
    ),
    PilotCase(
        "route",
        "The road links Encamp with Canillo.",
        (PilotSpan(15, 21, "3040686"), PilotSpan(27, 34, "3041204")),
    ),
    PilotCase(
        "catalan",
        "Andorra la Vella és a prop d'Escaldes-Engordany.",
        (PilotSpan(0, 16, "3041563"), PilotSpan(29, 47, "3338529")),
    ),
    PilotCase(
        "spanish",
        "Canillo y Encamp están en Andorra.",
        (
            PilotSpan(0, 7, "3041204"),
            PilotSpan(10, 16, "3040686"),
            PilotSpan(26, 33, "3041565"),
        ),
    ),
    PilotCase(
        "french",
        "À Encamp, les rues sont calmes.",
        (PilotSpan(2, 8, "3040686"),),
    ),
    PilotCase(
        "no-target-place",
        "A river crosses the market before winter arrives.",
        (),
    ),
    PilotCase(
        "non-andorran-distractor",
        "Paris is mentioned beside an unnamed city.",
        (),
    ),
)


def _gold_annotations(case: PilotCase) -> tuple[Annotation, ...]:
    """Convert fixed gold data to the library's evaluation value object."""
    from geoparser.evaluation import Annotation

    return tuple(
        Annotation(span.start, span.end, span.identifier) for span in case.gold
    )


def _limit_model_context(resolver: Any) -> None:
    """Bound the real resolver window for the short, fixed pilot documents."""
    resolver.transformer.max_seq_length = MAX_SEQUENCE_LENGTH


def _use_cpu_float32(resolver: Any) -> None:
    """Use the CPU-friendly dtype for the real Jina reranker."""
    resolver.reranker.float()


def _serialize_annotations(
    text: str, annotations: Sequence[Annotation]
) -> list[dict[str, object]]:
    """Serialize spans with their source text and optional resolution ID."""
    return [
        {
            "start": annotation.start,
            "end": annotation.end,
            "text": text[annotation.start : annotation.end],
            "identifier": annotation.identifier,
        }
        for annotation in annotations
    ]


def build_document_report(
    case: PilotCase, predicted: Sequence[Annotation], elapsed_ms: float
) -> Report:
    """Build one JSON-compatible record from observed model output."""
    from geoparser.evaluation import (
        recognition_f1,
        recognition_precision,
        recognition_recall,
        resolution_accuracy,
    )

    gold = _gold_annotations(case)
    predicted = tuple(predicted)
    return {
        "id": case.case_id,
        "text": case.text,
        "gold": _serialize_annotations(case.text, gold),
        "predicted": _serialize_annotations(case.text, predicted),
        "metrics": {
            "recognition": {
                "precision": recognition_precision(gold, predicted),
                "recall": recognition_recall(gold, predicted),
                "f1": recognition_f1(gold, predicted),
            },
            "resolution": {"accuracy": resolution_accuracy(gold, predicted)},
        },
        "elapsed_ms": round(elapsed_ms, 3),
    }


def build_report(
    cases: Sequence[PilotCase],
    predictions: Sequence[Sequence[Annotation]],
    timings_ms: Sequence[float],
    *,
    models: Mapping[str, str],
    configuration: Mapping[str, object] | None = None,
) -> Report:
    """Build the complete pilot report without loading any ML components."""
    if not (len(cases) == len(predictions) == len(timings_ms)):
        raise ValueError("cases, predictions, and timings_ms must have the same length")

    documents = [
        build_document_report(case, predicted, elapsed_ms)
        for case, predicted, elapsed_ms in zip(
            cases, predictions, timings_ms, strict=True
        )
    ]
    gold = tuple(annotation for case in cases for annotation in _gold_annotations(case))
    predicted = tuple(annotation for document in predictions for annotation in document)

    from geoparser.evaluation import (
        recognition_f1,
        recognition_precision,
        recognition_recall,
        resolution_accuracy,
    )

    return {
        "schema_version": 1,
        "models": dict(models),
        "configuration": dict(configuration or {}),
        "aggregate": {
            "document_count": len(cases),
            "gold_annotation_count": len(gold),
            "predicted_annotation_count": len(predicted),
            "recognition": {
                "precision": recognition_precision(gold, predicted),
                "recall": recognition_recall(gold, predicted),
                "f1": recognition_f1(gold, predicted),
            },
            "resolution": {"accuracy": resolution_accuracy(gold, predicted)},
        },
        "documents": documents,
    }


def _format_places(annotations: list[dict[str, object]]) -> str:
    """Format serialized annotations for the human-readable summary."""
    if not annotations:
        return "-"
    return ", ".join(
        f"{annotation['text']} ({annotation['identifier'] or 'unresolved'})"
        for annotation in annotations
    )


def render_markdown(report: Report) -> str:
    """Render a compact Markdown summary while JSON retains all evidence."""
    aggregate = report["aggregate"]
    recognition = aggregate["recognition"]
    resolution = aggregate["resolution"]
    model_lines = [f"- {name}: `{value}`" for name, value in report["models"].items()]
    lines = [
        "# Geoparsing pilot",
        "",
        "## Models",
        *model_lines,
        "",
        "## Aggregate",
        f"- Documents: {aggregate['document_count']}",
        f"- Gold annotations: {aggregate['gold_annotation_count']}",
        f"- Predicted annotations: {aggregate['predicted_annotation_count']}",
        f"- Recognition: precision {recognition['precision']:.3f}, "
        f"recall {recognition['recall']:.3f}, F1 {recognition['f1']:.3f}",
        f"- Resolution accuracy: {resolution['accuracy']:.3f}",
        "",
        "## Documents",
        "",
        "| ID | Gold spans | Predicted spans | F1 | Resolution | Elapsed (ms) |",
        "| --- | --- | --- | ---: | ---: | ---: |",
    ]
    for document in report["documents"]:
        metrics = document["metrics"]
        lines.append(
            f"| {document['id']} | {_format_places(document['gold'])} | "
            f"{_format_places(document['predicted'])} | "
            f"{metrics['recognition']['f1']:.3f} | "
            f"{metrics['resolution']['accuracy']:.3f} | {document['elapsed_ms']:.3f} |"
        )
    return "\n".join(lines) + "\n"


def write_report(report: Report, output_dir: Path) -> tuple[Path, Path]:
    """Write JSON evidence and a Markdown summary to a durable directory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "pilot-report.json"
    markdown_path = output_dir / "pilot-report.md"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    return json_path, markdown_path


def _configure_runtime(output_dir: Path, hf_home: Path | None, offline: bool) -> None:
    """Route the pilot database and gazetteer artifact to the output volume."""
    output_dir.mkdir(parents=True, exist_ok=True)
    database_path = output_dir / "pilot.sqlite"
    os.environ["DATABASE_URL"] = f"sqlite:///{database_path}"
    os.environ["GEOPARSER_GAZETTEERS_DIR"] = str(output_dir / "gazetteers")
    if hf_home is not None:
        os.environ["HF_HOME"] = str(hf_home)
    if offline:
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"


def _document_annotations(document: object) -> list[Annotation]:
    """Extract recognized spans and resolver IDs from a parsed document."""
    from geoparser.evaluation import Annotation

    return [
        Annotation(
            reference.start,
            reference.end,
            reference.location.identifier if reference.location is not None else None,
        )
        for reference in document.toponyms  # type: ignore[attr-defined]
    ]


def run_pilot(
    *,
    config_path: Path,
    output_dir: Path,
    hf_home: Path | None = None,
    offline: bool = False,
) -> tuple[Path, Path]:
    """Build the real gazetteer, parse all fixed cases, and persist evidence."""
    _configure_runtime(output_dir, hf_home, offline)

    # These imports intentionally happen after runtime paths are configured:
    # geoparser.db.db creates its engine at import time.
    import torch

    from geoparser.gazetteer.build import GazetteerBuilder
    from geoparser.modules import GLiNER2Recognizer, JinaResolver
    from geoparser.project import Project

    torch_threads = min(8, os.cpu_count() or 1)
    torch.set_num_threads(torch_threads)

    class TimedGLiNER2Recognizer(GLiNER2Recognizer):
        """Record one real recognition duration per input document."""

        def __init__(self) -> None:
            self.document_timings_ms: list[float] = []
            super().__init__()

        def _document_references(self, text: str) -> list[tuple[int, int]]:
            started = time.perf_counter()
            try:
                return super()._document_references(text)
            finally:
                self.document_timings_ms.append((time.perf_counter() - started) * 1000)

    class TimedJinaResolver(JinaResolver):
        """Record per-document resolution-decision durations in a batch."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.document_timings_ms: dict[str, float] = {}
            self._timing_texts: list[str] = []
            self._evaluation_index = 0
            super().__init__(*args, **kwargs)

        def predict(
            self, texts: list[str], references: list[list[tuple[int, int]]]
        ) -> list[list[tuple[str, str] | None]]:
            self.document_timings_ms = dict.fromkeys(texts, 0.0)
            self._timing_texts = texts
            return super().predict(texts, references)

        def _evaluate_candidates(self, *args: Any, **kwargs: Any) -> None:
            self._evaluation_index = 0
            super()._evaluate_candidates(*args, **kwargs)

        def _evaluate_document(self, *args: Any, **kwargs: Any) -> None:
            index = self._evaluation_index
            self._evaluation_index += 1
            started = time.perf_counter()
            try:
                super()._evaluate_document(*args, **kwargs)
            finally:
                if index < len(self._timing_texts):
                    text = self._timing_texts[index]
                    self.document_timings_ms[text] += (
                        time.perf_counter() - started
                    ) * 1000

    artifact_path = GazetteerBuilder().build(config_path)
    texts = [case.text for case in PILOT_CASES]
    project = Project(f"pilot-{uuid.uuid4().hex[:8]}")
    try:
        project.create_documents(texts)

        # Keep the two largest model graphs out of memory at the same time.
        # The project and service layers preserve the same end-to-end database
        # workflow as Geoparser.parse while making this resource boundary explicit.
        recognizer = TimedGLiNER2Recognizer()
        recognition_started = time.perf_counter()
        project.run_recognizer(recognizer)
        recognition_batch_elapsed_ms = (
            time.perf_counter() - recognition_started
        ) * 1000
        recognizer_model_name = recognizer.model_name
        recognition_timings_ms = tuple(recognizer.document_timings_ms)
        del recognizer
        gc.collect()

        resolver = TimedJinaResolver(
            gazetteer_name="andorranames",
            min_similarity=0.5,
            max_tiers=2,
            attribute_map=ANDORRA_ATTRIBUTE_MAP,
        )
        _limit_model_context(resolver)
        _use_cpu_float32(resolver)
        resolution_started = time.perf_counter()
        project.run_resolver(resolver)
        resolution_batch_elapsed_ms = (time.perf_counter() - resolution_started) * 1000
        documents = project.get_documents()
        predictions = [_document_annotations(document) for document in documents]
        timings_ms = [
            recognition_timings_ms[index]
            + resolver.document_timings_ms.get(case.text, 0.0)
            for index, case in enumerate(PILOT_CASES)
        ]
    finally:
        project.delete()

    report = build_report(
        PILOT_CASES,
        predictions,
        timings_ms,
        models={
            "recognizer": recognizer_model_name,
            "resolver_embedding": resolver.model_name,
            "resolver_reranker": resolver.reranker_name,
        },
        configuration={
            "gazetteer": "andorranames",
            "gazetteer_artifact": artifact_path.name,
            "min_similarity": 0.5,
            "max_tiers": 2,
            "rerank_top_k": resolver.rerank_top_k,
            "max_sequence_length": MAX_SEQUENCE_LENGTH,
            "reranker_dtype": str(next(resolver.reranker.parameters()).dtype),
            "torch_threads": torch_threads,
            "recognition_batch_elapsed_ms": round(recognition_batch_elapsed_ms, 3),
            "resolution_batch_elapsed_ms": round(resolution_batch_elapsed_ms, 3),
            "batch_elapsed_ms": round(
                recognition_batch_elapsed_ms + resolution_batch_elapsed_ms, 3
            ),
            "execution": (
                "Project.run_recognizer then Project.run_resolver with model release "
                "between phases"
            ),
            "timing_scope": (
                "per-document recognition plus resolution decisions; shared "
                "batch embedding time is reported separately"
            ),
            "gold_cases": len(PILOT_CASES),
        },
    )
    return write_report(report, output_dir)


def main(argv: list[str] | None = None) -> int:
    """Parse command-line arguments and run the pilot."""
    repository = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=repository / "tests/fixtures/gazetteer/andorranames.yaml",
        help="Gazetteer YAML configuration (default: the Andorra fixture).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=repository / "pilot-results",
        help="Durable directory for the artifact, database, and reports.",
    )
    parser.add_argument(
        "--hf-home",
        type=Path,
        default=Path(os.environ["HF_HOME"]) if os.getenv("HF_HOME") else None,
        help="Existing Hugging Face cache; no model is downloaded by this script.",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Require offline Hugging Face loading from the configured cache.",
    )
    args = parser.parse_args(argv)
    json_path, markdown_path = run_pilot(
        config_path=args.config,
        output_dir=args.output_dir,
        hf_home=args.hf_home,
        offline=args.offline,
    )
    print(f"JSON report: {json_path}")
    print(f"Markdown report: {markdown_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
