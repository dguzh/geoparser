"""
Tests for the context window the SentenceTransformerResolver builds.

These exercise the token accounting directly rather than through ``predict``:
the window is grown a sentence at a time against a budget, and getting the
arithmetic wrong silently produces contexts the encoder will truncate. A fake
tokenizer counts words, so the budget is easy to reason about in the tests.
"""

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest


def _sentence(text: str, start_char: int = 0) -> SimpleNamespace:
    """A stand-in for a spaCy sentence span."""
    return SimpleNamespace(
        text=text, start_char=start_char, end_char=start_char + len(text)
    )


def _sentences(*texts: str) -> list[SimpleNamespace]:
    """Consecutive sentence spans with contiguous character offsets."""
    spans = []
    offset = 0
    for text in texts:
        spans.append(_sentence(text, offset))
        offset += len(text) + 1
    return spans


@pytest.fixture
def resolver():
    """A resolver whose tokenizer counts words, with everything else mocked."""
    with (
        patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer"),
        patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer"),
        patch(
            "geoparser.modules.resolvers.sentencetransformer.AutoTokenizer.from_pretrained"
        ) as mock_tokenizer,
        patch("geoparser.modules.resolvers.sentencetransformer.spacy.load"),
    ):
        from geoparser.modules.resolvers.sentencetransformer import (
            SentenceTransformerResolver,
        )

        mock_tokenizer.return_value.tokenize = Mock(
            side_effect=lambda text: text.split()
        )
        return SentenceTransformerResolver()


@pytest.mark.unit
class TestSentenceTokens:
    """The per-sentence token cost."""

    def test_counts_the_tokenizer_output_for_the_sentence_text(self, resolver):
        """The cost is the tokenizer's length, not the character length."""
        # Arrange
        sentence = _sentence("one two three")

        # Act
        cost = resolver._sentence_tokens(sentence)

        # Assert
        assert cost == 3


@pytest.mark.unit
class TestAffordableCost:
    """Whether a neighbouring sentence exists and still fits."""

    def test_returns_the_cost_when_it_fits_exactly(self, resolver):
        """A neighbour costing exactly the remaining budget is affordable."""
        # Arrange
        sentences = _sentences("a b", "c d")

        # Act
        cost = resolver._affordable_cost(sentences, 1, remaining=2)

        # Assert
        assert cost == 2

    def test_returns_none_when_the_neighbour_is_one_token_too_expensive(self, resolver):
        """One token over budget is not affordable."""
        # Arrange
        sentences = _sentences("a b", "c d")

        # Act
        cost = resolver._affordable_cost(sentences, 1, remaining=1)

        # Assert
        assert cost is None

    @pytest.mark.parametrize("index", [-1, 2])
    def test_returns_none_off_either_end(self, resolver, index):
        """There is no sentence before the first or after the last."""
        # Arrange
        sentences = _sentences("a b", "c d")

        # Act
        cost = resolver._affordable_cost(sentences, index, remaining=100)

        # Assert
        assert cost is None


@pytest.mark.unit
class TestExpandWindow:
    """Growing the context window around the reference's sentence."""

    def test_returns_only_the_target_when_nothing_else_fits(self, resolver):
        """A budget that covers just the target sentence yields only it."""
        # Arrange
        sentences = _sentences("aa bb", "cc dd", "ee ff")

        # Act
        window = resolver._expand_window(sentences, target_idx=1, token_limit=2)

        # Assert
        assert [s.text for s in window] == ["cc dd"]

    def test_expands_in_both_directions_when_the_budget_allows(self, resolver):
        """With room for all three, the window covers the whole document."""
        # Arrange
        sentences = _sentences("aa bb", "cc dd", "ee ff")

        # Act
        window = resolver._expand_window(sentences, target_idx=1, token_limit=6)

        # Assert
        assert [s.text for s in window] == ["aa bb", "cc dd", "ee ff"]

    def test_takes_the_preceding_sentence_first(self, resolver):
        """With room for exactly one neighbour, the earlier one wins."""
        # Arrange
        sentences = _sentences("aa bb", "cc dd", "ee ff")

        # Act
        window = resolver._expand_window(sentences, target_idx=1, token_limit=4)

        # Assert
        assert [s.text for s in window] == ["aa bb", "cc dd"]

    def test_never_exceeds_the_token_budget(self, resolver):
        """
        The window must fit the budget it was given.

        This is the property that matters: an off-by-one, or adding the
        target's cost instead of subtracting it, produces a context the
        encoder silently truncates.
        """
        # Arrange
        sentences = _sentences(*[f"s{i} w w" for i in range(9)])

        for token_limit in range(3, 30):
            # Act
            window = resolver._expand_window(
                sentences, target_idx=4, token_limit=token_limit
            )

            # Assert
            spent = sum(len(s.text.split()) for s in window)
            assert spent <= token_limit, f"budget {token_limit} overspent by window"

    def test_keeps_growing_over_several_rounds(self, resolver):
        """
        Expansion continues while either neighbour still fits.

        Each round takes at most one sentence per side, so a budget with room
        for two on each side must be filled by two rounds. Stopping after the
        first would silently return a context less than half the size asked
        for.
        """
        # Arrange - seven two-token sentences, budget for exactly five
        sentences = _sentences(*[f"s{i} w" for i in range(7)])

        # Act
        window = resolver._expand_window(sentences, target_idx=3, token_limit=10)

        # Assert
        assert [s.text for s in window] == [
            "s1 w",
            "s2 w",
            "s3 w",
            "s4 w",
            "s5 w",
        ]

    def test_stops_at_the_start_of_the_document(self, resolver):
        """A target in the first sentence only grows forwards."""
        # Arrange
        sentences = _sentences("aa bb", "cc dd")

        # Act
        window = resolver._expand_window(sentences, target_idx=0, token_limit=100)

        # Assert
        assert [s.text for s in window] == ["aa bb", "cc dd"]

    def test_stops_at_the_end_of_the_document(self, resolver):
        """A target in the last sentence only grows backwards."""
        # Arrange
        sentences = _sentences("aa bb", "cc dd")

        # Act
        window = resolver._expand_window(sentences, target_idx=1, token_limit=100)

        # Assert
        assert [s.text for s in window] == ["aa bb", "cc dd"]

    def test_keeps_the_window_contiguous_and_ordered(self, resolver):
        """The window is a run of consecutive sentences, in document order."""
        # Arrange
        sentences = _sentences(*[f"s{i} w" for i in range(7)])

        # Act
        window = resolver._expand_window(sentences, target_idx=3, token_limit=8)

        # Assert
        indices = [sentences.index(s) for s in window]
        assert indices == list(range(indices[0], indices[0] + len(indices)))
        assert 3 in indices


@pytest.mark.unit
class TestLocateSentence:
    """Finding the sentence that holds a reference."""

    def test_returns_the_index_of_the_containing_sentence(self, resolver):
        """A reference inside the second sentence resolves to index 1."""
        # Arrange
        sentences = _sentences("aa bb", "cc dd", "ee ff")

        # Act
        index = resolver._locate_sentence(sentences, start=6, end=8)

        # Assert
        assert index == 1

    def test_matches_the_first_character_of_a_sentence(self, resolver):
        """The span start is inclusive."""
        # Arrange
        sentences = _sentences("aa bb", "cc dd")

        # Act & Assert
        assert resolver._locate_sentence(sentences, start=0, end=2) == 0
        assert resolver._locate_sentence(sentences, start=6, end=8) == 1

    def test_rejects_an_offset_past_the_last_sentence(self, resolver):
        """An offset no sentence covers is reported, not silently mapped."""
        # Arrange
        sentences = _sentences("aa bb")

        # Act & Assert
        with pytest.raises(ValueError, match="No sentence contains reference"):
            resolver._locate_sentence(sentences, start=99, end=100)
