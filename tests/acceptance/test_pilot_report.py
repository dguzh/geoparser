import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from geoparser.evaluation import Annotation
from scripts.pilot import PilotCase, PilotSpan, build_report

pytestmark = pytest.mark.acceptance
scenarios("features/pilot_report.feature")


@pytest.fixture
def pilot_state() -> dict[str, object]:
    return {}


@given(parsers.parse('the pilot observed "{text}"'))
def observed_text(pilot_state: dict[str, object], text: str) -> None:
    pilot_state["text"] = text


@given(parsers.parse('the gold place is "{place}" with identifier "{identifier}"'))
def gold_place(pilot_state: dict[str, object], place: str, identifier: str) -> None:
    text = pilot_state["text"]
    assert isinstance(text, str)
    start = text.index(place)
    pilot_state["gold"] = PilotSpan(start, start + len(place), identifier)


@given(parsers.parse('the predicted place is "{place}" with identifier "{identifier}"'))
def predicted_place(
    pilot_state: dict[str, object], place: str, identifier: str
) -> None:
    text = pilot_state["text"]
    assert isinstance(text, str)
    start = text.index(place)
    pilot_state["predicted"] = Annotation(start, start + len(place), identifier)


@when("I build the pilot report")
def build_pilot_report(pilot_state: dict[str, object]) -> None:
    text = pilot_state["text"]
    gold = pilot_state["gold"]
    predicted = pilot_state["predicted"]
    assert isinstance(text, str)
    assert isinstance(gold, PilotSpan)
    assert isinstance(predicted, Annotation)

    pilot_state["report"] = build_report(
        (PilotCase("acceptance", text, (gold,)),),
        ((predicted,),),
        (0.0,),
        models={"recognizer": "acceptance"},
        configuration={"gazetteer": "andorranames"},
    )


@then("the report recognition F1 is 1.0")
def report_recognition_f1_is_perfect(pilot_state: dict[str, object]) -> None:
    report = pilot_state["report"]
    assert report["aggregate"]["recognition"]["f1"] == 1.0


@then("the report resolution accuracy is 1.0")
def report_resolution_is_perfect(pilot_state: dict[str, object]) -> None:
    report = pilot_state["report"]
    assert report["aggregate"]["resolution"]["accuracy"] == 1.0


@then(parsers.parse('the report preserves the span text "{place}"'))
def report_preserves_span_text(pilot_state: dict[str, object], place: str) -> None:
    report = pilot_state["report"]
    assert report["documents"][0]["predicted"][0]["text"] == place
