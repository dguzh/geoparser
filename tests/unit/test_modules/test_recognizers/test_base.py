"""
Unit tests for geoparser/modules/recognizers/base.py

Tests the Recognizer base class.
"""

import pytest

from geoparser.modules.recognizers.base import Recognizer


# Create a concrete implementation for testing
class ConcreteRecognizer(Recognizer):
    """Concrete implementation of Recognizer for testing purposes."""

    NAME = "TestRecognizer"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def predict(self, texts):
        """Dummy implementation for testing."""
        return [[(0, 4)] for _ in texts]


@pytest.mark.unit
class TestRecognizerInitialization:
    """Test Recognizer initialization."""

    def test_inherits_from_module(self):
        """Test that Recognizer inherits from Module base class."""
        # Arrange & Act
        from geoparser.modules.module import Module

        # Assert
        assert issubclass(Recognizer, Module)

    def test_base_class_has_none_name(self):
        """Test that Recognizer base class has NAME set to None."""
        # Assert
        assert Recognizer.NAME is None

    def test_cannot_instantiate_base_recognizer(self):
        """Test that base Recognizer class cannot be instantiated directly."""
        # Act & Assert
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            Recognizer()

    def test_concrete_recognizer_can_be_instantiated(self):
        """Test that concrete Recognizer implementation can be instantiated."""
        # Arrange & Act
        recognizer = ConcreteRecognizer()

        # Assert
        assert recognizer.name == "TestRecognizer"

    def test_stores_config_parameters(self):
        """Test that Recognizer stores configuration parameters."""
        # Arrange & Act
        recognizer = ConcreteRecognizer(param1="value1", param2=42)

        # Assert
        assert recognizer.config["param1"] == "value1"
        assert recognizer.config["param2"] == 42


@pytest.mark.unit
class TestRecognizerPredict:
    """Test Recognizer predict method."""

    def test_predict_is_abstract_method(self):
        """Test that predict is defined as an abstract method."""
        # Arrange
        from abc import ABCMeta

        # Assert - Recognizer should be abstract
        assert isinstance(Recognizer, ABCMeta)
        # predict should be in abstract methods
        assert "predict" in Recognizer.__abstractmethods__

    def test_concrete_implementation_must_implement_predict(self):
        """Test that concrete implementations must implement predict method."""

        # Arrange - Create a class without predict implementation
        class IncompleteRecognizer(Recognizer):
            NAME = "Incomplete"
            # Missing predict implementation

        # Act & Assert
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteRecognizer()

    def test_predict_signature_accepts_texts(self):
        """Test that predict method accepts a list of texts."""
        # Arrange
        recognizer = ConcreteRecognizer()
        texts = ["Text 1", "Text 2"]

        # Act
        result = recognizer.predict(texts)

        # Assert - Should return results
        assert len(result) == 2

    def test_predict_returns_list_of_references(self):
        """Test that predict returns list of reference lists."""
        # Arrange
        recognizer = ConcreteRecognizer()
        texts = ["Test text"]

        # Act
        result = recognizer.predict(texts)

        # Assert
        assert isinstance(result, list)
        assert isinstance(result[0], list)
        assert isinstance(result[0][0], tuple)
        assert len(result[0][0]) == 2  # (start, end) tuple
