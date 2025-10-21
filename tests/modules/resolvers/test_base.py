import pytest

from geoparser.modules.resolvers.base import Resolver


def test_resolver_initialization():
    """Test basic initialization of Resolver."""

    class TestResolver(Resolver):
        NAME = "test_resolver"

        def predict(self, texts, references):
            return [[("gazetteer", "id1") for _ in doc_refs] for doc_refs in references]

    resolver = TestResolver(param1="value1")
    assert resolver.name == "test_resolver"
    assert resolver.config == {"param1": "value1"}


def test_resolver_abstract():
    """Test that Resolver is abstract and requires implementation."""

    # Create a concrete subclass that doesn't implement required methods
    class InvalidResolver(Resolver):
        NAME = "invalid_resolver"

    # Should raise TypeError when instantiated due to abstract methods
    with pytest.raises(TypeError, match="predict"):
        InvalidResolver()


def test_predict_referents_implementation():
    """Test a valid implementation of predict."""

    class ValidResolver(Resolver):
        NAME = "valid_resolver"

        def predict(self, texts, references):
            return [
                [("test_gazetteer", "loc1") for _ in doc_refs]
                for doc_refs in references
            ]

    resolver = ValidResolver()

    # Test with raw data format
    texts = ["Test document 1", "Test document 2"]
    references = [[(0, 5)], [(10, 15)]]  # One reference per document

    result = resolver.predict(texts, references)
    assert len(result) == 2
    assert len(result[0]) == 1
    assert result[0][0] == ("test_gazetteer", "loc1")
    assert len(result[1]) == 1
    assert result[1][0] == ("test_gazetteer", "loc1")
