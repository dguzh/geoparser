"""
Unit tests for geoparser/db/models/name.py

Tests the Name model.
"""

import pytest
from sqlmodel import Session

from geoparser.db.models import NameCreate, NameUpdate


@pytest.mark.unit
class TestNameModel:
    """Test the Name model."""

    def test_creates_name_with_valid_data(self, test_session: Session, feature_factory):
        """Test that a Name can be created with valid data."""
        # Arrange
        from geoparser.db.models import Name

        feature = feature_factory()
        name = Name(text="Paris", feature_id=feature.id)

        # Act
        test_session.add(name)
        test_session.commit()
        test_session.refresh(name)

        # Assert
        assert name.id is not None
        assert isinstance(name.id, int)
        assert name.text == "Paris"
        assert name.feature_id == feature.id

    def test_generates_integer_id_automatically(
        self, test_session: Session, feature_factory
    ):
        """Test that Name automatically generates an integer ID."""
        # Arrange
        from geoparser.db.models import Name

        feature = feature_factory()
        name = Name(text="London", feature_id=feature.id)

        # Act
        test_session.add(name)
        test_session.commit()

        # Assert
        assert name.id is not None
        assert isinstance(name.id, int)

    def test_text_is_indexed(self, test_session: Session, feature_factory):
        """Test that the text field is indexed for efficient queries."""
        # Arrange
        from sqlmodel import select

        from geoparser.db.models import Name

        feature = feature_factory()
        name = Name(text="Indexed Name", feature_id=feature.id)
        test_session.add(name)
        test_session.commit()

        # Act - Query by text should work efficiently
        statement = select(Name).where(Name.text == "Indexed Name")
        result = test_session.exec(statement).first()

        # Assert
        assert result is not None
        assert result.text == "Indexed Name"

    def test_has_feature_relationship(self, test_session: Session):
        """Test that Name has a relationship to feature."""
        # Arrange
        from geoparser.db.models import Name

        name = Name(text="Test", feature_id=1)

        # Assert
        assert hasattr(name, "feature")

    def test_has_unique_constraint_on_text_and_feature(
        self, test_session: Session, feature_factory
    ):
        """Test that Name has unique constraint on (text, feature_id)."""
        # Arrange
        from sqlalchemy.exc import IntegrityError

        from geoparser.db.models import Name

        feature = feature_factory()
        name1 = Name(text="Paris", feature_id=feature.id)
        test_session.add(name1)
        test_session.commit()

        # Act & Assert - Try to create duplicate
        name2 = Name(text="Paris", feature_id=feature.id)
        test_session.add(name2)

        with pytest.raises(IntegrityError):
            test_session.commit()

    def test_allows_same_text_for_different_features(
        self, test_session: Session, feature_factory
    ):
        """Test that same text can be used for different features."""
        # Arrange
        from geoparser.db.models import Name

        feature1 = feature_factory()
        feature2 = feature_factory(
            source_id=feature1.source_id, location_id_value="456"
        )

        name1 = Name(text="Paris", feature_id=feature1.id)
        name2 = Name(text="Paris", feature_id=feature2.id)

        # Act
        test_session.add(name1)
        test_session.add(name2)
        test_session.commit()

        # Assert - Both should be created successfully
        assert name1.id is not None
        assert name2.id is not None
        assert name1.id != name2.id

    def test_str_representation(self, test_session: Session):
        """Test that Name has a useful string representation."""
        # Arrange
        from geoparser.db.models import Name

        name = Name(text="Paris", feature_id=1)

        # Act
        str_repr = str(name)

        # Assert
        assert "Name" in str_repr
        assert "Paris" in str_repr

    def test_repr_matches_str(self, test_session: Session):
        """Test that __repr__ matches __str__."""
        # Arrange
        from geoparser.db.models import Name

        name = Name(text="London", feature_id=1)

        # Act & Assert
        assert repr(name) == str(name)


@pytest.mark.unit
class TestNameCreate:
    """Test the NameCreate model."""

    def test_creates_with_required_fields(self):
        """Test that NameCreate can be created with required fields."""
        # Arrange & Act
        name_create = NameCreate(text="Paris", feature_id=123)

        # Assert
        assert name_create.text == "Paris"
        assert name_create.feature_id == 123


@pytest.mark.unit
class TestNameUpdate:
    """Test the NameUpdate model."""

    def test_creates_update_with_all_fields(self):
        """Test that NameUpdate can be created with all fields."""
        # Arrange & Act
        name_update = NameUpdate(id=1, text="Updated Name", feature_id=456)

        # Assert
        assert name_update.id == 1
        assert name_update.text == "Updated Name"
        assert name_update.feature_id == 456

    def test_allows_optional_fields(self):
        """Test that NameUpdate allows optional fields."""
        # Arrange & Act
        name_update = NameUpdate(id=1)

        # Assert
        assert name_update.id == 1
        assert name_update.text is None
        assert name_update.feature_id is None
