"""
Executable acceptance scenarios for sizing a reference's context.

These read as the behaviour a resolver author relies on: which sentences end
up in the context for a given document and budget. They drive the real
selection code, with sentence costs stated directly so each scenario says
exactly what it depends on.
"""

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from geoparser.modules.resolvers.context import Sentence, select_context

pytestmark = pytest.mark.acceptance
scenarios("features/context_window.feature")


@pytest.fixture
def context_state() -> dict[str, object]:
    """What each scenario builds up as its steps run."""
    return {}


def _document(costs: list[int]) -> list[Sentence]:
    """A document whose sentences carry the given token costs."""
    sentences = []
    offset = 0
    for index, cost in enumerate(costs):
        text = f"sentence-{index}"
        sentences.append(
            Sentence(text=text, start=offset, end=offset + len(text), cost=cost)
        )
        offset += len(text) + 1
    return sentences


@given(parsers.parse("a document whose sentences cost {costs} tokens"))
def document(context_state: dict[str, object], costs: str) -> None:
    context_state["sentences"] = _document([int(part) for part in costs.split(",")])


@given(parsers.parse("the encoder can afford {budget:d} tokens"))
def budget(context_state: dict[str, object], budget: int) -> None:
    context_state["budget"] = budget


@when(parsers.parse("I size the context around the sentence at index {index:d}"))
def size_context(context_state: dict[str, object], index: int) -> None:
    sentences = context_state["sentences"]
    assert isinstance(sentences, list)
    target = sentences[index]
    context_state["context"] = select_context(
        sentences, target.start, target.end, context_state["budget"]
    )


@when("I size the context around an offset past the end of the document")
def size_context_past_end(context_state: dict[str, object]) -> None:
    sentences = context_state["sentences"]
    assert isinstance(sentences, list)
    past_end = sentences[-1].end + 5
    try:
        select_context(sentences, past_end, past_end + 1, context_state["budget"])
    except ValueError as error:
        context_state["error"] = error


@then(parsers.parse("the context covers sentences {first:d} to {last:d}"))
def context_covers(context_state: dict[str, object], first: int, last: int) -> None:
    sentences = context_state["sentences"]
    assert isinstance(sentences, list)
    expected = " ".join(item.text for item in sentences[first : last + 1])
    assert context_state["context"] == expected


@then(parsers.parse("the context costs at most {budget:d} tokens"))
def context_costs_at_most(context_state: dict[str, object], budget: int) -> None:
    sentences = context_state["sentences"]
    assert isinstance(sentences, list)
    context = context_state["context"]
    included = [item for item in sentences if item.text in str(context).split()]
    assert sum(item.cost for item in included) <= budget


@then("sizing fails because no sentence contains the reference")
def sizing_fails(context_state: dict[str, object]) -> None:
    error = context_state.get("error")
    assert isinstance(error, ValueError)
    assert "No sentence contains reference" in str(error)
