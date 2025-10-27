"""
Unit tests for geoparser/modules/__init__.py

Tests the lazy-loading module initialization.
"""

import pytest


@pytest.mark.unit
class TestModulesLazyLoading:
    """Test modules/__init__.py lazy-loading functionality."""

    def test_lazy_loads_spacy_recognizer(self):
        """Test that SpacyRecognizer is lazy-loaded on access."""
        # Arrange & Act
        from geoparser.modules import SpacyRecognizer

        # Assert
        assert SpacyRecognizer is not None
        assert SpacyRecognizer.__name__ == "SpacyRecognizer"

    def test_lazy_loads_sentence_transformer_resolver(self):
        """Test that SentenceTransformerResolver is lazy-loaded on access."""
        # Arrange & Act
        from geoparser.modules import SentenceTransformerResolver

        # Assert
        assert SentenceTransformerResolver is not None
        assert SentenceTransformerResolver.__name__ == "SentenceTransformerResolver"

    def test_raises_attribute_error_for_unknown_module(self):
        """Test that AttributeError is raised for unknown module attributes."""
        # Arrange
        import geoparser.modules

        # Act & Assert
        with pytest.raises(
            AttributeError, match="has no attribute 'NonExistentModule'"
        ):
            _ = geoparser.modules.NonExistentModule
