import pytest

from geoparser.modules.recognizers.base import Recognizer


def test_recognizer_initialization():
    """Test basic initialization of Recognizer."""

    class TestRecognizer(Recognizer):
        NAME = "test_recognizer"

        def predict(self, texts):
            return [[(0, 5)] for _ in texts]

    recognizer = TestRecognizer(param1="value1")
    assert recognizer.name == "test_recognizer"
    assert recognizer.config == {"param1": "value1"}


def test_recognizer_abstract():
    """Test that Recognizer is abstract and requires implementation."""

    # Create a concrete subclass that doesn't implement required methods
    class InvalidRecognizer(Recognizer):
        NAME = "invalid_recognizer"

    # Should raise TypeError when instantiated due to abstract methods
    with pytest.raises(TypeError, match="predict"):
        InvalidRecognizer()


def test_predict_references_implementation():
    """Test a valid implementation of predict."""

    class ValidRecognizer(Recognizer):
        NAME = "valid_recognizer"

        def predict(self, texts):
            return [[(0, 5), (10, 15)] for _ in texts]

    recognizer = ValidRecognizer()

    # Test with raw text strings
    texts = ["Test document 1", "Test document 2"]

    result = recognizer.predict(texts)
    assert len(result) == 2
    assert result[0] == [(0, 5), (10, 15)]
    assert result[1] == [(0, 5), (10, 15)]
