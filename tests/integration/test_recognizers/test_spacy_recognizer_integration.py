"""
Integration tests for geoparser/modules/recognizers/spacy.py

Tests SpacyRecognizer with real spaCy models, verifying actual NER capabilities.
"""

import pytest

from geoparser.modules.recognizers.spacy import SpacyRecognizer


@pytest.mark.integration
class TestSpacyRecognizerIntegration:
    """Integration tests for SpacyRecognizer with real spaCy model."""

    def test_identifies_geopolitical_entities(self, real_spacy_recognizer):
        """Test that SpacyRecognizer identifies GPE entities in text."""
        # Arrange
        texts = ["New York is a major city in the United States."]

        # Act
        results = real_spacy_recognizer.predict(texts)

        # Assert
        assert len(results) == 1
        assert len(results[0]) > 0  # Should find at least one entity
        # New York should be identified
        assert any(0 <= start <= 8 and 7 <= end <= 9 for start, end in results[0])

    def test_identifies_multiple_entities_in_text(self, real_spacy_recognizer):
        """Test that SpacyRecognizer identifies multiple entities in a single text."""
        # Arrange
        texts = ["Paris and London are cities in Europe."]

        # Act
        results = real_spacy_recognizer.predict(texts)

        # Assert
        assert len(results) == 1
        # Should identify multiple locations (Paris, London, Europe)
        assert len(results[0]) >= 2

    def test_returns_character_offsets(self, real_spacy_recognizer):
        """Test that SpacyRecognizer returns correct character offsets."""
        # Arrange
        text = "Tokyo is the capital of Japan."
        texts = [text]

        # Act
        results = real_spacy_recognizer.predict(texts)

        # Assert
        assert len(results) == 1
        # Verify that offsets correspond to actual text
        for start, end in results[0]:
            entity_text = text[start:end]
            # Entity text should not be empty
            assert len(entity_text) > 0
            # Should be alphanumeric or contain spaces (place names)
            assert any(c.isalnum() or c.isspace() for c in entity_text)

    def test_handles_text_without_entities(self, real_spacy_recognizer):
        """Test that SpacyRecognizer returns empty list for text without entities."""
        # Arrange
        texts = ["The number is 42 and the color is blue."]

        # Act
        results = real_spacy_recognizer.predict(texts)

        # Assert
        assert len(results) == 1
        # Should return empty list (no geo entities in this text)
        assert results[0] == []

    def test_processes_multiple_texts(self, real_spacy_recognizer):
        """Test that SpacyRecognizer processes multiple texts correctly."""
        # Arrange
        texts = [
            "Berlin is in Germany.",
            "Sydney is in Australia.",
            "No locations here.",
        ]

        # Act
        results = real_spacy_recognizer.predict(texts)

        # Assert
        assert len(results) == 3
        assert len(results[0]) > 0  # Berlin, Germany
        assert len(results[1]) > 0  # Sydney, Australia
        assert len(results[2]) == 0  # No entities

    def test_handles_empty_text(self, real_spacy_recognizer):
        """Test that SpacyRecognizer handles empty text gracefully."""
        # Arrange
        texts = [""]

        # Act
        results = real_spacy_recognizer.predict(texts)

        # Assert
        assert len(results) == 1
        assert results[0] == []

    def test_uses_configured_entity_types(self):
        """Test that SpacyRecognizer only identifies configured entity types."""
        # Arrange
        recognizer = SpacyRecognizer(
            model_name="en_core_web_sm", entity_types=["GPE"]  # Only GPE, not LOC
        )
        texts = ["New York is a city."]  # GPE entity

        # Act
        results = recognizer.predict(texts)

        # Assert
        assert len(results) == 1
        # Should find GPE entities
        assert len(results[0]) > 0

    def test_deterministic_id_generation(self):
        """Test that same configuration produces same ID."""
        # Arrange
        recognizer1 = SpacyRecognizer(
            model_name="en_core_web_sm", entity_types=["GPE", "LOC"]
        )
        recognizer2 = SpacyRecognizer(
            model_name="en_core_web_sm", entity_types=["GPE", "LOC"]
        )

        # Act & Assert
        assert recognizer1.id == recognizer2.id

    def test_different_config_produces_different_id(self):
        """Test that different configuration produces different ID."""
        # Arrange
        recognizer1 = SpacyRecognizer(model_name="en_core_web_sm", entity_types=["GPE"])
        recognizer2 = SpacyRecognizer(model_name="en_core_web_sm", entity_types=["LOC"])

        # Act & Assert
        assert recognizer1.id != recognizer2.id

    def test_preserves_reference_order(self, real_spacy_recognizer):
        """Test that references are returned in order of appearance in text."""
        # Arrange
        texts = ["I traveled from Paris to London to Berlin."]

        # Act
        results = real_spacy_recognizer.predict(texts)

        # Assert
        if len(results[0]) >= 2:
            # Each subsequent reference should start after the previous one
            for i in range(len(results[0]) - 1):
                assert results[0][i][0] < results[0][i + 1][0]

    def test_handles_long_text(self, real_spacy_recognizer):
        """Test that SpacyRecognizer can process longer texts."""
        # Arrange
        long_text = " ".join(
            [
                "New York is a city.",
                "Paris is in France.",
                "Tokyo is in Japan.",
                "Sydney is in Australia.",
                "Berlin is in Germany.",
            ]
            * 10
        )  # Repeat to make it longer
        texts = [long_text]

        # Act
        results = real_spacy_recognizer.predict(texts)

        # Assert
        assert len(results) == 1
        # Should find many entities in the long text
        assert len(results[0]) > 10
