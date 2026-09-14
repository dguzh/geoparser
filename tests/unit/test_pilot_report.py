import json
from types import SimpleNamespace

import pytest

from geoparser.evaluation import Annotation
from scripts.pilot import (
    MAX_SEQUENCE_LENGTH,
    PILOT_CASES,
    PilotCase,
    PilotSpan,
    _limit_model_context,
    _use_cpu_float32,
    build_report,
    write_report,
)


def test_pilot_bounds_context_length_for_short_fixture_documents() -> None:
    resolver = SimpleNamespace(transformer=SimpleNamespace(max_seq_length=8192))

    _limit_model_context(resolver)

    assert MAX_SEQUENCE_LENGTH == 128
    assert resolver.transformer.max_seq_length == MAX_SEQUENCE_LENGTH


def test_pilot_uses_float32_for_cpu_model_inference() -> None:
    class FakeModel:
        def __init__(self) -> None:
            self.converted = False

        def float(self):
            self.converted = True
            return self

    resolver = SimpleNamespace(transformer=FakeModel(), reranker=FakeModel())

    _use_cpu_float32(resolver)

    assert not resolver.transformer.converted
    assert resolver.reranker.converted


def test_pilot_cases_have_valid_hand_written_gold_spans() -> None:
    assert len(PILOT_CASES) == 13
    assert sum(len(case.gold) for case in PILOT_CASES) == 15

    for case in PILOT_CASES:
        for span in case.gold:
            assert 0 <= span.start < span.end <= len(case.text)
            assert case.text[span.start : span.end].strip()
            assert span.identifier.isdigit()


def test_build_report_records_annotations_metrics_and_timings() -> None:
    cases = (
        PilotCase(
            "capital",
            "Andorra la Vella is the capital.",
            (PilotSpan(0, 16, "3041563"),),
        ),
        PilotCase("empty", "Nothing is named here.", ()),
    )
    predictions = (
        (Annotation(0, 16, "3041563"),),
        (),
    )

    report = build_report(
        cases,
        predictions,
        (12.34567, 2.0),
        models={"recognizer": "recognizer-test"},
        configuration={"gazetteer": "andorranames"},
    )

    assert report["schema_version"] == 1
    assert report["models"] == {"recognizer": "recognizer-test"}
    assert report["configuration"] == {"gazetteer": "andorranames"}
    assert report["aggregate"] == {
        "document_count": 2,
        "gold_annotation_count": 1,
        "predicted_annotation_count": 1,
        "recognition": {"precision": 1.0, "recall": 1.0, "f1": 1.0},
        "resolution": {"accuracy": 1.0},
    }
    assert report["documents"][0] == {
        "id": "capital",
        "text": "Andorra la Vella is the capital.",
        "gold": [
            {
                "start": 0,
                "end": 16,
                "text": "Andorra la Vella",
                "identifier": "3041563",
            }
        ],
        "predicted": [
            {
                "start": 0,
                "end": 16,
                "text": "Andorra la Vella",
                "identifier": "3041563",
            }
        ],
        "metrics": {
            "recognition": {"precision": 1.0, "recall": 1.0, "f1": 1.0},
            "resolution": {"accuracy": 1.0},
        },
        "elapsed_ms": 12.346,
    }


def test_build_report_rejects_misaligned_inputs() -> None:
    case = PilotCase("one", "One.", ())

    with pytest.raises(ValueError, match="same length"):
        build_report((case,), (), (), models={})


def test_write_report_emits_json_and_markdown(tmp_path) -> None:
    report = build_report(
        (PilotCase("empty", "Nothing.", ()),),
        ((),),
        (0.5,),
        models={"recognizer": "recognizer-test"},
        configuration={"gazetteer": "andorranames"},
    )

    json_path, markdown_path = write_report(report, tmp_path)

    assert json.loads(json_path.read_text()) == report
    markdown = markdown_path.read_text()
    assert "# Geoparsing pilot" in markdown
    assert "recognizer-test" in markdown
    assert "| empty |" in markdown
