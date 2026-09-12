"""
Unit tests for geoparser/modules/resolvers/context.py

Sizing a reference's context is arithmetic over sentence costs and a budget:
which sentence holds the reference, and how far outwards the window can grow
before the encoder would truncate it. None of that needs a tokenizer, a
sentence splitter or an embedding model -- only the costs those produce -- so
these tests construct sentences directly and mock nothing.
"""

import pytest

from geoparser.modules.resolvers.context import (
    Sentence,
    expand_window,
    locate_sentence,
    select_context,
)


def _sentences(*costs: int) -> list[Sentence]:
    """Consecutive sentences of the given token costs, one word each."""
    sentences = []
    offset = 0
    for index, cost in enumerate(costs):
        text = f"s{index}"
        sentences.append(
            Sentence(text=text, start=offset, end=offset + len(text), cost=cost)
        )
        offset += len(text) + 1
    return sentences


@pytest.mark.unit
class TestSentence:
    """The value object the rest of the module works over."""

    def test_carries_its_text_span_and_cost(self):
        """A sentence knows where it is, what it says and what it costs."""
        # Act
        sentence = Sentence(text="Paris.", start=4, end=10, cost=3)

        # Assert
        assert (sentence.text, sentence.start, sentence.end, sentence.cost) == (
            "Paris.",
            4,
            10,
            3,
        )

    def test_covers_offsets_from_start_up_to_but_not_including_end(self):
        """The span is half-open, like every other span in the library."""
        # Arrange
        sentence = Sentence(text="Paris.", start=4, end=10, cost=3)

        # Act & Assert
        assert sentence.covers(4)
        assert sentence.covers(9)
        assert not sentence.covers(10)
        assert not sentence.covers(3)

    def test_is_immutable(self):
        """Sentences are values, so a window cannot alter the document."""
        # Arrange
        sentence = Sentence(text="Paris.", start=0, end=6, cost=3)

        # Act & Assert
        with pytest.raises(AttributeError):
            sentence.cost = 99


@pytest.mark.unit
class TestLocateSentence:
    """Finding the sentence a reference falls in."""

    def test_returns_the_index_of_the_containing_sentence(self):
        """The reference's start offset selects the sentence."""
        # Arrange
        sentences = _sentences(1, 1, 1)

        # Act & Assert
        assert locate_sentence(sentences, 3, 5) == 1

    def test_matches_the_first_character_of_a_sentence(self):
        """A reference at a sentence boundary belongs to the sentence it opens."""
        # Arrange
        sentences = _sentences(1, 1)

        # Act & Assert
        assert locate_sentence(sentences, 0, 2) == 0
        assert locate_sentence(sentences, 3, 5) == 1

    def test_rejects_an_offset_no_sentence_covers(self):
        """A span past the end of the text is reported, not silently mapped."""
        # Arrange
        sentences = _sentences(1)

        # Act & Assert
        with pytest.raises(ValueError, match="position 99-104"):
            locate_sentence(sentences, 99, 104)

    def test_rejects_an_offset_in_a_gap_between_sentences(self):
        """A splitter that leaves a gap is a problem the caller must hear about."""
        # Arrange - a hole between offsets 5 and 10
        sentences = [
            Sentence(text="aaaaa", start=0, end=5, cost=1),
            Sentence(text="bbbbb", start=10, end=15, cost=1),
        ]

        # Act & Assert
        with pytest.raises(ValueError, match="position 7-8"):
            locate_sentence(sentences, 7, 8)

    def test_rejects_an_empty_document(self):
        """No sentences means nothing can contain the reference."""
        # Act & Assert
        with pytest.raises(ValueError):
            locate_sentence([], 0, 1)


@pytest.mark.unit
class TestExpandWindow:
    """Growing the window outwards under a budget."""

    def test_returns_only_the_target_when_nothing_else_fits(self):
        """A budget that covers just the target yields just the target."""
        # Arrange
        sentences = _sentences(3, 3, 3)

        # Act
        window = expand_window(sentences, 1, budget=3)

        # Assert
        assert window == [sentences[1]]

    def test_expands_in_both_directions_when_the_budget_allows(self):
        """Room on both sides is used on both sides."""
        # Arrange
        sentences = _sentences(2, 2, 2)

        # Act
        window = expand_window(sentences, 1, budget=6)

        # Assert
        assert window == sentences

    def test_takes_the_preceding_sentence_first(self):
        """
        With room for exactly one neighbour, the earlier one wins.

        Preceding text is what usually disambiguates a place name, so the tie
        is broken deliberately rather than by iteration order.
        """
        # Arrange
        sentences = _sentences(2, 2, 2)

        # Act
        window = expand_window(sentences, 1, budget=4)

        # Assert
        assert window == [sentences[0], sentences[1]]

    def test_never_exceeds_the_budget(self):
        """A neighbour one token too expensive is left out."""
        # Arrange
        sentences = _sentences(5, 2, 5)

        # Act
        window = expand_window(sentences, 1, budget=6)

        # Assert
        assert window == [sentences[1]]

    def test_keeps_growing_over_several_rounds(self):
        """Each round takes at most one sentence per side, so rounds repeat."""
        # Arrange - seven sentences of two tokens, budget for five
        sentences = _sentences(*[2] * 7)

        # Act
        window = expand_window(sentences, 3, budget=10)

        # Assert
        assert window == sentences[1:6]

    def test_keeps_growing_backwards_at_the_end_of_the_document(self):
        """One-sided growth continues across rounds too."""
        # Arrange
        sentences = _sentences(*[2] * 4)

        # Act
        window = expand_window(sentences, 3, budget=6)

        # Assert
        assert window == sentences[1:4]

    def test_keeps_growing_forwards_at_the_start_of_the_document(self):
        """The same holds at the other edge."""
        # Arrange
        sentences = _sentences(*[2] * 4)

        # Act
        window = expand_window(sentences, 0, budget=6)

        # Assert
        assert window == sentences[0:3]

    def test_returns_the_target_even_when_it_alone_exceeds_the_budget(self):
        """
        An oversized sentence is still the context.

        The encoder will truncate it, but returning an empty context would
        lose the reference altogether, which is strictly worse.
        """
        # Arrange
        sentences = _sentences(2, 50, 2)

        # Act
        window = expand_window(sentences, 1, budget=10)

        # Assert
        assert window == [sentences[1]]

    def test_a_single_sentence_document_returns_that_sentence(self):
        """There is nowhere to grow."""
        # Arrange
        sentences = _sentences(1)

        # Act & Assert
        assert expand_window(sentences, 0, budget=100) == sentences

    def test_a_zero_cost_neighbour_is_taken(self):
        """Something that costs nothing always fits."""
        # Arrange
        sentences = _sentences(0, 1, 0)

        # Act
        window = expand_window(sentences, 1, budget=1)

        # Assert
        assert window == sentences


@pytest.mark.unit
class TestSelectContext:
    """The whole selection, from sentences and a reference to a string."""

    def test_joins_the_window_sentences_with_a_single_space(self):
        """Selected sentences are rejoined as plain prose."""
        # Arrange
        sentences = [
            Sentence(text="aa bb.", start=0, end=6, cost=2),
            Sentence(text="cc dd.", start=7, end=13, cost=2),
            Sentence(text="ee ff.", start=14, end=20, cost=2),
        ]

        # Act
        context = select_context(sentences, 7, 9, budget=5)

        # Assert
        assert context == "aa bb. cc dd."

    def test_returns_the_target_sentence_when_the_budget_is_tight(self):
        """A budget with no room to spare still returns the reference's own text."""
        # Arrange
        sentences = [
            Sentence(text="aa bb.", start=0, end=6, cost=2),
            Sentence(text="cc dd.", start=7, end=13, cost=2),
        ]

        # Act & Assert
        assert select_context(sentences, 7, 9, budget=2) == "cc dd."

    def test_reports_a_reference_that_falls_in_no_sentence(self):
        """The failure names the span so the caller can find it."""
        # Arrange
        sentences = [Sentence(text="aa bb.", start=0, end=6, cost=2)]

        # Act & Assert
        with pytest.raises(ValueError, match="position 40-45"):
            select_context(sentences, 40, 45, budget=100)
