"""
Property tests for the context window.

The window is chosen by arithmetic over sentence costs, and the arithmetic has
to hold for any document and any budget, not only the handful of shapes the
unit tests spell out. These generate documents and budgets and assert the
properties the resolver depends on: the reference is always in the context,
the context is a contiguous run of whole sentences, it respects the budget
whenever that is possible at all, and it is as large as the budget allows.
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from geoparser.modules.resolvers.context import (
    Sentence,
    expand_window,
    locate_sentence,
    select_context,
)

PROPERTY_SETTINGS = settings(deadline=None, derandomize=True, database=None)

COSTS = st.lists(st.integers(min_value=0, max_value=40), min_size=1, max_size=12)
BUDGETS = st.integers(min_value=0, max_value=120)


def _document(costs: list[int]) -> list[Sentence]:
    """A document whose sentences carry the given token costs."""
    sentences = []
    offset = 0
    for index, cost in enumerate(costs):
        text = f"s{index}" * max(cost, 1)
        sentences.append(
            Sentence(text=text, start=offset, end=offset + len(text), cost=cost)
        )
        offset += len(text) + 1
    return sentences


@st.composite
def documents_with_target(draw):
    """A document, and the index of one of its sentences."""
    costs = draw(COSTS)
    sentences = _document(costs)
    return sentences, draw(st.integers(min_value=0, max_value=len(sentences) - 1))


@pytest.mark.property
@PROPERTY_SETTINGS
@given(documents_with_target(), BUDGETS)
def test_the_window_always_contains_the_target_sentence(document, budget):
    """
    Whatever the budget, the reference's own sentence is in the context.

    Losing it would hand the encoder text that does not contain the place
    name it is being asked to disambiguate.
    """
    sentences, target = document

    window = expand_window(sentences, target, budget)

    assert sentences[target] in window


@pytest.mark.property
@PROPERTY_SETTINGS
@given(documents_with_target(), BUDGETS)
def test_the_window_is_a_contiguous_run_in_document_order(document, budget):
    """The context is a slice of the document, not a selection from it."""
    sentences, target = document

    window = expand_window(sentences, target, budget)

    first = sentences.index(window[0])
    assert window == sentences[first : first + len(window)]


@pytest.mark.property
@PROPERTY_SETTINGS
@given(documents_with_target(), BUDGETS)
def test_the_window_fits_the_budget_unless_the_target_alone_cannot(document, budget):
    """
    The only context allowed to exceed the budget is a single oversized
    sentence, which the encoder will truncate rather than lose entirely.
    """
    sentences, target = document

    window = expand_window(sentences, target, budget)

    total = sum(sentence.cost for sentence in window)
    assert total <= budget or window == [sentences[target]]


@pytest.mark.property
@PROPERTY_SETTINGS
@given(documents_with_target(), BUDGETS)
def test_neither_neighbour_of_the_window_would_have_fitted(document, budget):
    """
    The window is maximal: it stopped because nothing more fitted.

    Without this, a window could satisfy every other property by simply being
    smaller than it needed to be, wasting the budget the encoder was given.
    """
    sentences, target = document

    window = expand_window(sentences, target, budget)

    spent = sum(sentence.cost for sentence in window)
    remaining = budget - spent
    first = sentences.index(window[0])
    last = first + len(window) - 1
    neighbours = [
        sentences[index]
        for index in (first - 1, last + 1)
        if 0 <= index < len(sentences)
    ]
    assert all(neighbour.cost > remaining for neighbour in neighbours)


@pytest.mark.property
@PROPERTY_SETTINGS
@given(documents_with_target(), BUDGETS)
def test_a_bigger_budget_never_gives_a_smaller_window(document, budget):
    """Growing the budget cannot cost the caller context."""
    sentences, target = document

    smaller = expand_window(sentences, target, budget)
    larger = expand_window(sentences, target, budget + 1)

    assert len(larger) >= len(smaller)


@pytest.mark.property
@PROPERTY_SETTINGS
@given(documents_with_target())
def test_every_sentence_is_locatable_from_any_offset_it_covers(document):
    """A reference anywhere inside a sentence resolves to that sentence."""
    sentences, target = document
    sentence = sentences[target]

    for offset in (sentence.start, sentence.end - 1):
        assert locate_sentence(sentences, offset, offset + 1) == target


@pytest.mark.property
@PROPERTY_SETTINGS
@given(documents_with_target(), BUDGETS)
def test_the_context_is_the_window_joined_by_single_spaces(document, budget):
    """select_context is expand_window plus a join, and nothing else."""
    sentences, target = document
    sentence = sentences[target]

    context = select_context(sentences, sentence.start, sentence.end, budget)

    window = expand_window(sentences, target, budget)
    assert context == " ".join(item.text for item in window)


@pytest.mark.property
@PROPERTY_SETTINGS
@given(documents_with_target(), BUDGETS)
def test_the_context_always_contains_the_reference_text(document, budget):
    """The place name the caller asked about is in the string it gets back."""
    sentences, target = document
    sentence = sentences[target]

    context = select_context(sentences, sentence.start, sentence.end, budget)

    assert sentence.text in context


@pytest.mark.property
@PROPERTY_SETTINGS
@given(
    st.lists(st.integers(min_value=0, max_value=20), min_size=1, max_size=8),
    st.integers(min_value=0, max_value=60),
)
def test_an_offset_past_the_document_is_always_rejected(costs, budget):
    """A span beyond the text is reported rather than mapped to a sentence."""
    sentences = _document(costs)
    past_end = sentences[-1].end + 1

    with pytest.raises(ValueError):
        select_context(sentences, past_end, past_end + 1, budget)
