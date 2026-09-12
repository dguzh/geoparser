"""
Tests for the seam between the resolver's models and its context sizing.

The arithmetic that chooses a context window lives in
``geoparser.modules.resolvers.context`` and is tested there, directly and
without mocks. What remains here is the part that genuinely needs the
resolver: turning spaCy's spans and the tokenizer's counts into the priced
sentences that arithmetic works over, and the decision to skip it entirely
when the whole document already fits.
"""

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from geoparser.modules.resolvers.context import Sentence


def _sentence(text: str, start_char: int = 0) -> SimpleNamespace:
    """A stand-in for a spaCy sentence span."""
    return SimpleNamespace(
        text=text, start_char=start_char, end_char=start_char + len(text)
    )


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


@pytest.fixture
def parsing_resolver(resolver):
    """A resolver whose spaCy pipeline splits on '. ' and counts words."""

    def parse(text):
        spans, offset = [], 0
        for chunk in text.split(". "):
            piece = chunk if offset + len(chunk) >= len(text) else chunk + "."
            spans.append(_sentence(piece, offset))
            offset += len(piece) + 1
        return SimpleNamespace(sents=spans)

    resolver.nlp = Mock(side_effect=parse)
    resolver.transformer.get_max_seq_length = Mock(return_value=7)
    return resolver


@pytest.mark.unit
class TestSentenceTokens:
    """The per-sentence token cost."""

    def test_counts_the_tokenizer_output_for_the_sentence_text(self, resolver):
        """The cost is the tokenizer's length, not the character length."""
        # Arrange
        sentence = _sentence("one two three")

        # Act & Assert
        assert resolver._sentence_tokens(sentence) == 3


@pytest.mark.unit
class TestMeasuredSentences:
    """Turning spaCy spans into priced sentences."""

    def test_prices_every_sentence_of_the_document(self, parsing_resolver):
        """Each span becomes one Sentence carrying its own token cost."""
        # Act
        sentences = parsing_resolver._measured_sentences("aa bb. cc dd ee.")

        # Assert
        assert sentences == [
            Sentence(text="aa bb.", start=0, end=6, cost=2),
            Sentence(text="cc dd ee.", start=7, end=16, cost=3),
        ]

    def test_keeps_spacys_own_character_offsets(self, resolver):
        """
        The offsets come from the span, not from re-measuring the text.

        A span's text and its character offsets are not always the same length
        apart -- trailing whitespace is the usual reason -- so recomputing the
        end from the text would shift every later reference.
        """
        # Arrange - a span whose end_char runs past its text
        span = SimpleNamespace(text="aa bb", start_char=4, end_char=12)
        resolver.nlp = Mock(return_value=SimpleNamespace(sents=[span]))

        # Act
        (sentence,) = resolver._measured_sentences("....aa bb   ")

        # Assert
        assert (sentence.start, sentence.end) == (4, 12)

    def test_parses_each_document_only_once(self, parsing_resolver):
        """The parsed document is cached, so a second reference is free."""
        # Arrange
        text = "aa bb. cc dd."

        # Act
        parsing_resolver._measured_sentences(text)
        parsing_resolver._measured_sentences(text)

        # Assert
        parsing_resolver.nlp.assert_called_once_with(text)


@pytest.mark.unit
class TestExtractContext:
    """The whole context extraction, from document text to context string."""

    def test_returns_the_whole_text_when_it_exactly_fills_the_budget(
        self, parsing_resolver
    ):
        """
        A document of exactly the budget is returned whole.

        The comparison is inclusive: treating a document that just fits as too
        long would send it through the windowing path for no reason.
        """
        # Arrange - five tokens, budget of seven minus two special tokens
        text = "aa bb cc. dd ee"

        # Act
        context = parsing_resolver._extract_context(text, 0, 2)

        # Assert
        assert context == text
        parsing_resolver.nlp.assert_not_called()

    def test_windows_a_document_that_does_not_fit(self, parsing_resolver):
        """A document over budget is trimmed to the sentences around the span."""
        # Arrange - three sentences, only two of which fit the budget
        text = "aa bb. cc dd. ee ff"

        # Act
        context = parsing_resolver._extract_context(text, 7, 9)

        # Assert
        assert context == "aa bb. cc dd."

    def test_parses_the_document_that_was_passed_in(self, parsing_resolver):
        """The sentence splitter sees the document text, not something else."""
        # Arrange
        text = "aa bb. cc dd. ee ff"

        # Act
        parsing_resolver._extract_context(text, 0, 2)

        # Assert
        parsing_resolver.nlp.assert_called_once_with(text)

    def test_names_the_whole_reference_span_when_no_sentence_contains_it(
        self, parsing_resolver
    ):
        """The error reports both offsets, so the caller can find the span."""
        # Arrange
        text = "aa bb. cc dd. ee ff"

        # Act & Assert
        with pytest.raises(ValueError, match="position 99-104"):
            parsing_resolver._extract_context(text, 99, 104)

    def test_counts_the_document_only_once(self, parsing_resolver):
        """The document's own token count is cached across references."""
        # Arrange
        text = "aa bb cc. dd ee"
        parsing_resolver.tokenizer.tokenize.reset_mock()

        # Act
        parsing_resolver._extract_context(text, 0, 2)
        parsing_resolver._extract_context(text, 3, 5)

        # Assert
        assert parsing_resolver.tokenizer.tokenize.call_count == 1
