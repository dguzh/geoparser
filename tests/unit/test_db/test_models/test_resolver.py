"""
Unit tests for geoparser/db/models/resolver.py

Tests the Resolver model.
"""

import pytest
from sqlmodel import Session

from geoparser.db.models import ResolverCreate, ResolverUpdate


@pytest.mark.unit
class TestResolverModel:
    """Test the Resolver model."""

    def test_creates_resolver_with_valid_data(
        self, test_session: Session, resolver_factory
    ):
        """Test that a Resolver can be created with valid data."""
        # Arrange & Act
        resolver = resolver_factory(
            id="test_res", name="Test Resolver", config={"param": "value"}
        )

        # Assert
        assert resolver.id == "test_res"
        assert resolver.name == "Test Resolver"
        assert resolver.config == {"param": "value"}

    def test_uses_string_as_primary_key(self, test_session: Session, resolver_factory):
        """Test that Resolver uses string ID as primary key."""
        # Arrange & Act
        resolver = resolver_factory(id="custom_id")

        # Assert
        assert resolver.id == "custom_id"
        assert isinstance(resolver.id, str)

    def test_name_is_indexed(self, test_session: Session, resolver_factory):
        """Test that the name field is indexed for efficient queries."""
        # Arrange
        resolver = resolver_factory(name="Indexed Resolver")

        # Act - Query by name should work efficiently
        from sqlmodel import select

        from geoparser.db.models import Resolver

        statement = select(Resolver).where(Resolver.name == "Indexed Resolver")
        result = test_session.exec(statement).first()

        # Assert
        assert result is not None
        assert result.name == "Indexed Resolver"

    def test_config_defaults_to_empty_dict(self, test_session: Session):
        """Test that config defaults to empty dictionary."""
        # Arrange
        from geoparser.db.models import Resolver

        resolver = Resolver(id="test", name="Test")

        # Act
        test_session.add(resolver)
        test_session.commit()
        test_session.refresh(resolver)

        # Assert
        assert resolver.config == {}

    def test_config_stores_json_data(self, test_session: Session, resolver_factory):
        """Test that config can store complex JSON data."""
        # Arrange
        config = {
            "model_name": "test_model",
            "gazetteer_name": "geonames",
            "min_similarity": 0.7,
            "nested": {"key": "value"},
        }

        # Act
        resolver = resolver_factory(config=config)

        # Assert
        assert resolver.config == config

    def test_has_referents_relationship(self, test_session: Session, resolver_factory):
        """Test that Resolver has a relationship to referents."""
        # Arrange
        resolver = resolver_factory()

        # Assert
        assert hasattr(resolver, "referents")
        assert isinstance(resolver.referents, list)

    def test_has_resolutions_relationship(
        self, test_session: Session, resolver_factory
    ):
        """Test that Resolver has a relationship to resolutions."""
        # Arrange
        resolver = resolver_factory()

        # Assert
        assert hasattr(resolver, "resolutions")
        assert isinstance(resolver.resolutions, list)

    def test_str_representation_with_config(
        self, test_session: Session, resolver_factory
    ):
        """Test that Resolver has a useful string representation with config."""
        # Arrange
        resolver = resolver_factory(
            name="TestResolver", config={"param1": "value1", "param2": 42}
        )

        # Act
        str_repr = str(resolver)

        # Assert
        assert "TestResolver" in str_repr
        assert "param1" in str_repr
        assert "value1" in str_repr

    def test_str_representation_without_config(
        self, test_session: Session, resolver_factory
    ):
        """Test that Resolver string representation works with empty config."""
        # Arrange
        resolver = resolver_factory(name="TestResolver", config={})

        # Act
        str_repr = str(resolver)

        # Assert
        assert str_repr == "TestResolver()"

    def test_repr_matches_str(self, test_session: Session, resolver_factory):
        """Test that __repr__ matches __str__."""
        # Arrange
        resolver = resolver_factory(name="TestResolver")

        # Act & Assert
        assert repr(resolver) == str(resolver)


@pytest.mark.unit
class TestResolverCreate:
    """Test the ResolverCreate model."""

    def test_creates_with_required_fields(self):
        """Test that ResolverCreate can be created with required fields."""
        # Arrange & Act
        resolver_create = ResolverCreate(id="test_id", name="Test Resolver")

        # Assert
        assert resolver_create.id == "test_id"
        assert resolver_create.name == "Test Resolver"

    def test_config_defaults_to_empty_dict(self):
        """Test that config defaults to empty dictionary in ResolverCreate."""
        # Arrange & Act
        resolver_create = ResolverCreate(id="test", name="Test")

        # Assert
        assert resolver_create.config == {}

    def test_can_include_config(self):
        """Test that ResolverCreate can include config."""
        # Arrange & Act
        resolver_create = ResolverCreate(
            id="test", name="Test", config={"key": "value"}
        )

        # Assert
        assert resolver_create.config == {"key": "value"}


@pytest.mark.unit
class TestResolverUpdate:
    """Test the ResolverUpdate model."""

    def test_creates_update_with_all_fields(self):
        """Test that ResolverUpdate can be created with all fields."""
        # Arrange & Act
        resolver_update = ResolverUpdate(
            id="test_id", name="Updated Name", config={"new": "config"}
        )

        # Assert
        assert resolver_update.id == "test_id"
        assert resolver_update.name == "Updated Name"
        assert resolver_update.config == {"new": "config"}

    def test_allows_optional_fields(self):
        """Test that ResolverUpdate allows optional fields."""
        # Arrange & Act
        resolver_update = ResolverUpdate(id="test_id")

        # Assert
        assert resolver_update.id == "test_id"
        assert resolver_update.name is None
        assert resolver_update.config is None
