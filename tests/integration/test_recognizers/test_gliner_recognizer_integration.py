"""
Integration tests for geoparser/modules/recognizers/gliner.py

These load the real GLiNER2.5 checkpoint and check that it actually finds
places, which the mocked unit tests cannot: they pin how the model's output is
reshaped, not that the labels this module asks for are ones the model responds
to. Getting the label wording wrong is a silent failure -- a zero-shot model
asked for a label it does not understand simply returns nothing.

The checkpoint is a large download, so these are opt-in: set
``GEOPARSER_TEST_REMOTE_MODELS=1`` to run them.
"""

import os

import pytest

from geoparser.modules.recognizers.gliner import GLiNER2Recognizer

pytestmark = pytest.mark.skipif(
    not os.getenv("GEOPARSER_TEST_REMOTE_MODELS"),
    reason="Set GEOPARSER_TEST_REMOTE_MODELS=1 to download and run GLiNER2.",
)


@pytest.fixture(scope="module")
def recognizer() -> GLiNER2Recognizer:
    """The real recognizer, loaded once for this module."""
    return GLiNER2Recognizer()


@pytest.mark.integration
class TestGLiNER2RecognizerIntegration:
    """The real model, on real text."""

    def test_finds_a_city_and_a_country(self, recognizer):
        """Both kinds of place in one sentence are found."""
        # Arrange
        text = "Tokyo is the capital of Japan."

        # Act
        (references,) = recognizer.predict([text])

        # Assert
        found = {text[start:end] for start, end in references}
        assert "Tokyo" in found
        assert "Japan" in found

    def test_the_offsets_index_the_document_text(self, recognizer):
        """Every span slices out the place name it stands for."""
        # Arrange
        text = "Paris and London are cities in Europe."

        # Act
        (references,) = recognizer.predict([text])

        # Assert
        assert references
        for start, end in references:
            assert text[start:end].strip() == text[start:end]
            assert text[start:end]

    def test_the_spans_come_back_in_document_order(self, recognizer):
        """References follow the text, not the model's label grouping."""
        # Arrange
        text = "From Lisbon to Warsaw, by way of Vienna."

        # Act
        (references,) = recognizer.predict([text])

        # Assert
        assert references == sorted(references)

    def test_a_sentence_with_no_places_yields_nothing(self, recognizer):
        """The model is not made to invent references."""
        # Act
        (references,) = recognizer.predict(["The kettle finished boiling."])

        # Assert
        assert references == []

    def test_recognizes_places_in_a_non_english_sentence(self, recognizer):
        """
        The multilingual checkpoint earns its name.

        This is the reason to prefer it over a per-language NER pipeline, and
        it is the one property no amount of English test text would reveal.
        """
        # Arrange
        text = "Berlin ist die Hauptstadt von Deutschland."

        # Act
        (references,) = recognizer.predict([text])

        # Assert
        found = {text[start:end] for start, end in references}
        assert "Berlin" in found

    def test_a_custom_label_finds_what_the_defaults_miss(self, recognizer):
        """Zero-shot labels are the point: asking for rivers finds rivers."""
        # Arrange
        text = "The Danube flows past Budapest."
        rivers = GLiNER2Recognizer(entity_types=["river"])

        # Act
        (found,) = rivers.predict([text])

        # Assert
        assert "Danube" in {text[start:end] for start, end in found}

    def test_batches_are_returned_document_for_document(self, recognizer):
        """A batch keeps its order and its length."""
        # Arrange
        texts = ["Oslo is cold.", "Nothing here.", "Cairo is warm."]

        # Act
        results = recognizer.predict(texts)

        # Assert
        assert len(results) == 3
        assert results[1] == []
        assert results[0] and results[2]
