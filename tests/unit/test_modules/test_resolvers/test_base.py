"""
Unit tests for geoparser/modules/resolvers/base.py

Tests the Resolver base class.
"""

import pytest

from geoparser.modules.resolvers.base import Resolver


# Create a concrete implementation for testing
class ConcreteResolver(Resolver):
    """Concrete implementation of Resolver for testing purposes."""

    NAME = "TestResolver"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def predict(self, texts, references):
        """Dummy implementation for testing."""
        return [[("geonames", "123") for _ in doc_refs] for doc_refs in references]


@pytest.mark.unit
class TestResolverInitialization:
    """Test Resolver initialization."""

    def test_inherits_from_module(self):
        """Test that Resolver inherits from Module base class."""
        # Arrange & Act
        from geoparser.modules.module import Module

        # Assert
        assert issubclass(Resolver, Module)

    def test_base_class_has_none_name(self):
        """Test that Resolver base class has NAME set to None."""
        # Assert
        assert Resolver.NAME is None

    def test_cannot_instantiate_base_resolver(self):
        """Test that base Resolver class cannot be instantiated directly."""
        # Act & Assert
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            Resolver()

    def test_concrete_resolver_can_be_instantiated(self):
        """Test that concrete Resolver implementation can be instantiated."""
        # Arrange & Act
        resolver = ConcreteResolver()

        # Assert
        assert resolver.name == "TestResolver"

    def test_stores_config_parameters(self):
        """Test that Resolver stores configuration parameters."""
        # Arrange & Act
        resolver = ConcreteResolver(param1="value1", param2=42)

        # Assert
        assert resolver.config["param1"] == "value1"
        assert resolver.config["param2"] == 42


@pytest.mark.unit
class TestResolverPredict:
    """Test Resolver predict method."""

    def test_predict_is_abstract_method(self):
        """Test that predict is defined as an abstract method."""
        # Arrange
        from abc import ABCMeta

        # Assert - Resolver should be abstract
        assert isinstance(Resolver, ABCMeta)
        # predict should be in abstract methods
        assert "predict" in Resolver.__abstractmethods__

    def test_concrete_implementation_must_implement_predict(self):
        """Test that concrete implementations must implement predict method."""

        # Arrange - Create a class without predict implementation
        class IncompleteResolver(Resolver):
            NAME = "Incomplete"
            # Missing predict implementation

        # Act & Assert
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteResolver()

    def test_predict_signature_accepts_texts_and_references(self):
        """Test that predict method accepts texts and references."""
        # Arrange
        resolver = ConcreteResolver()
        texts = ["Text 1"]
        references = [[(0, 4)]]

        # Act
        result = resolver.predict(texts, references)

        # Assert - Should return results
        assert len(result) == 1

    def test_predict_returns_list_of_referents(self):
        """Test that predict returns list of referent lists."""
        # Arrange
        resolver = ConcreteResolver()
        texts = ["Test"]
        references = [[(0, 4)]]

        # Act
        result = resolver.predict(texts, references)

        # Assert
        assert isinstance(result, list)
        assert isinstance(result[0], list)
        assert isinstance(result[0][0], tuple)
        assert len(result[0][0]) == 2  # (gazetteer_name, identifier) tuple

    def test_predict_returns_none_for_unresolved_references(self):
        """Test that predict can return None for unresolved references."""

        # Arrange - Create resolver that returns None for some references
        class PartialResolver(Resolver):
            NAME = "PartialResolver"

            def predict(self, texts, references):
                return [[("geonames", "123"), None] for _ in texts]

        resolver = PartialResolver()
        texts = ["Test"]
        references = [[(0, 4), (5, 9)]]

        # Act
        result = resolver.predict(texts, references)

        # Assert
        assert result[0][0] == ("geonames", "123")
        assert result[0][1] is None
