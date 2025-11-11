"""
Unit tests for geoparser/db/models/recognizer.py

Tests the Recognizer model.
"""

import pytest
from sqlmodel import Session

from geoparser.db.models import RecognizerCreate, RecognizerUpdate


@pytest.mark.unit
class TestRecognizerModel:
    """Test the Recognizer model."""

    def test_creates_recognizer_with_valid_data(
        self, test_session: Session, recognizer_factory
    ):
        """Test that a Recognizer can be created with valid data."""
        # Arrange & Act
        recognizer = recognizer_factory(
            id="test_rec", name="Test Recognizer", config={"param": "value"}
        )

        # Assert
        assert recognizer.id == "test_rec"
        assert recognizer.name == "Test Recognizer"
        assert recognizer.config == {"param": "value"}

    def test_uses_string_as_primary_key(
        self, test_session: Session, recognizer_factory
    ):
        """Test that Recognizer uses string ID as primary key."""
        # Arrange & Act
        recognizer = recognizer_factory(id="custom_id")

        # Assert
        assert recognizer.id == "custom_id"
        assert isinstance(recognizer.id, str)

    def test_name_is_indexed(self, test_session: Session, recognizer_factory):
        """Test that the name field is indexed for efficient queries."""
        # Arrange
        recognizer = recognizer_factory(name="Indexed Recognizer")

        # Act - Query by name should work efficiently
        from sqlmodel import select

        from geoparser.db.models import Recognizer

        statement = select(Recognizer).where(Recognizer.name == "Indexed Recognizer")
        result = test_session.exec(statement).first()

        # Assert
        assert result is not None
        assert result.name == "Indexed Recognizer"

    def test_config_defaults_to_empty_dict(self, test_session: Session):
        """Test that config defaults to empty dictionary."""
        # Arrange
        from geoparser.db.models import Recognizer

        recognizer = Recognizer(id="test", name="Test")

        # Act
        test_session.add(recognizer)
        test_session.commit()
        test_session.refresh(recognizer)

        # Assert
        assert recognizer.config == {}

    def test_config_stores_json_data(self, test_session: Session, recognizer_factory):
        """Test that config can store complex JSON data."""
        # Arrange
        config = {
            "model_name": "test_model",
            "entity_types": ["GPE", "LOC"],
            "nested": {"key": "value"},
        }

        # Act
        recognizer = recognizer_factory(config=config)

        # Assert
        assert recognizer.config == config

    def test_has_references_relationship(
        self, test_session: Session, recognizer_factory
    ):
        """Test that Recognizer has a relationship to references."""
        # Arrange
        recognizer = recognizer_factory()

        # Assert
        assert hasattr(recognizer, "references")
        assert isinstance(recognizer.references, list)

    def test_has_recognitions_relationship(
        self, test_session: Session, recognizer_factory
    ):
        """Test that Recognizer has a relationship to recognitions."""
        # Arrange
        recognizer = recognizer_factory()

        # Assert
        assert hasattr(recognizer, "recognitions")
        assert isinstance(recognizer.recognitions, list)

    def test_str_representation_with_config(
        self, test_session: Session, recognizer_factory
    ):
        """Test that Recognizer has a useful string representation with config."""
        # Arrange
        recognizer = recognizer_factory(
            name="TestRecognizer", config={"param1": "value1", "param2": 42}
        )

        # Act
        str_repr = str(recognizer)

        # Assert
        assert "TestRecognizer" in str_repr
        assert "param1" in str_repr
        assert "value1" in str_repr

    def test_str_representation_without_config(
        self, test_session: Session, recognizer_factory
    ):
        """Test that Recognizer string representation works with empty config."""
        # Arrange
        recognizer = recognizer_factory(name="TestRecognizer", config={})

        # Act
        str_repr = str(recognizer)

        # Assert
        assert str_repr == "TestRecognizer()"

    def test_repr_matches_str(self, test_session: Session, recognizer_factory):
        """Test that __repr__ matches __str__."""
        # Arrange
        recognizer = recognizer_factory(name="TestRecognizer")

        # Act & Assert
        assert repr(recognizer) == str(recognizer)


@pytest.mark.unit
class TestRecognizerCreate:
    """Test the RecognizerCreate model."""

    def test_creates_with_required_fields(self):
        """Test that RecognizerCreate can be created with required fields."""
        # Arrange & Act
        recognizer_create = RecognizerCreate(id="test_id", name="Test Recognizer")

        # Assert
        assert recognizer_create.id == "test_id"
        assert recognizer_create.name == "Test Recognizer"

    def test_config_defaults_to_empty_dict(self):
        """Test that config defaults to empty dictionary in RecognizerCreate."""
        # Arrange & Act
        recognizer_create = RecognizerCreate(id="test", name="Test")

        # Assert
        assert recognizer_create.config == {}

    def test_can_include_config(self):
        """Test that RecognizerCreate can include config."""
        # Arrange & Act
        recognizer_create = RecognizerCreate(
            id="test", name="Test", config={"key": "value"}
        )

        # Assert
        assert recognizer_create.config == {"key": "value"}


@pytest.mark.unit
class TestRecognizerUpdate:
    """Test the RecognizerUpdate model."""

    def test_creates_update_with_all_fields(self):
        """Test that RecognizerUpdate can be created with all fields."""
        # Arrange & Act
        recognizer_update = RecognizerUpdate(
            id="test_id", name="Updated Name", config={"new": "config"}
        )

        # Assert
        assert recognizer_update.id == "test_id"
        assert recognizer_update.name == "Updated Name"
        assert recognizer_update.config == {"new": "config"}

    def test_allows_optional_fields(self):
        """Test that RecognizerUpdate allows optional fields."""
        # Arrange & Act
        recognizer_update = RecognizerUpdate(id="test_id")

        # Assert
        assert recognizer_update.id == "test_id"
        assert recognizer_update.name is None
        assert recognizer_update.config is None
