import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from geoparser.geoparser import Geoparser
from geoparser.modules.recognizers.manual import ManualRecognizer
from geoparser.modules.resolvers.manual import ManualResolver


pytestmark = pytest.mark.acceptance
scenarios("features")


@pytest.fixture
def parse_state() -> dict[str, object]:
    return {}


@given(parsers.parse('the document "{text}"'))
def document(parse_state: dict[str, object], text: str) -> None:
    parse_state["text"] = text


@given(parsers.parse("the document has the place span from {start:d} to {end:d}"))
def place_span(parse_state: dict[str, object], start: int, end: int) -> None:
    parse_state["span"] = (start, end)


@given(parsers.parse('the place resolves to Andorra feature "{identifier}"'))
def place_referent(parse_state: dict[str, object], identifier: str) -> None:
    parse_state["referent"] = ("andorranames", identifier)


@when("I parse the document with the manual pipeline")
def parse_document(parse_state: dict[str, object], andorra_gazetteer) -> None:
    text = parse_state["text"]
    span = parse_state["span"]
    referent = parse_state["referent"]
    assert isinstance(text, str)
    assert isinstance(span, tuple)
    assert isinstance(referent, tuple)

    recognizer = ManualRecognizer(
        label="acceptance-recognizer", texts=[text], references=[[span]]
    )
    resolver = ManualResolver(
        label="acceptance-resolver",
        texts=[text],
        references=[[span]],
        referents=[[referent]],
    )
    parse_state["document"] = Geoparser(
        recognizer=recognizer, resolver=resolver
    ).parse(text, save=False)


@then(parsers.parse('the parsed document text is "{text}"'))
def parsed_text(parse_state: dict[str, object], text: str) -> None:
    document = parse_state["document"]
    assert document.text == text


@then(parsers.parse('it contains one place span "{text}"'))
def parsed_place(parse_state: dict[str, object], text: str) -> None:
    document = parse_state["document"]
    assert len(document.toponyms) == 1
    assert document.toponyms[0].text == text


@then(parsers.parse('the place identifier is "{identifier}"'))
def parsed_identifier(parse_state: dict[str, object], identifier: str) -> None:
    document = parse_state["document"]
    assert document.toponyms[0].location is not None
    assert document.toponyms[0].location.identifier == identifier
