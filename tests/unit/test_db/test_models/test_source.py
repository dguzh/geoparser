"""
Unit tests for geoparser/db/models/source.py

Tests the Source model.
"""

import uuid

import pytest
from sqlmodel import Session

from geoparser.db.models import SourceCreate, SourceUpdate


@pytest.mark.unit
class TestSourceModel:
    """Test the Source model."""

    def test_creates_source_with_valid_data(
        self, test_session: Session, gazetteer_factory
    ):
        """Test that a Source can be created with valid data."""
        # Arrange
        from geoparser.db.models import Source

        gazetteer = gazetteer_factory()
        source = Source(
            name="geonames_main",
            location_id_name="geonameid",
            gazetteer_id=gazetteer.id,
        )

        # Act
        test_session.add(source)
        test_session.commit()
        test_session.refresh(source)

        # Assert
        assert source.id is not None
        assert isinstance(source.id, int)
        assert source.name == "geonames_main"
        assert source.location_id_name == "geonameid"
        assert source.gazetteer_id == gazetteer.id

    def test_generates_integer_id_automatically(
        self, test_session: Session, gazetteer_factory
    ):
        """Test that Source automatically generates an integer ID."""
        # Arrange
        from geoparser.db.models import Source

        gazetteer = gazetteer_factory()
        source = Source(name="test", location_id_name="id", gazetteer_id=gazetteer.id)

        # Act
        test_session.add(source)
        test_session.commit()

        # Assert
        assert source.id is not None
        assert isinstance(source.id, int)

    def test_name_is_indexed(self, test_session: Session, gazetteer_factory):
        """Test that the name field is indexed for efficient queries."""
        # Arrange
        from sqlmodel import select

        from geoparser.db.models import Source

        gazetteer = gazetteer_factory()
        source = Source(
            name="Indexed Source", location_id_name="id", gazetteer_id=gazetteer.id
        )
        test_session.add(source)
        test_session.commit()

        # Act - Query by name should work efficiently
        statement = select(Source).where(Source.name == "Indexed Source")
        result = test_session.exec(statement).first()

        # Assert
        assert result is not None
        assert result.name == "Indexed Source"

    def test_has_gazetteer_relationship(self, test_session: Session):
        """Test that Source has a relationship to gazetteer."""
        # Arrange
        from geoparser.db.models import Source

        source = Source(name="test", location_id_name="id", gazetteer_id=uuid.uuid4())

        # Assert
        assert hasattr(source, "gazetteer")

    def test_has_features_relationship(self, test_session: Session):
        """Test that Source has a relationship to features."""
        # Arrange
        from geoparser.db.models import Source

        source = Source(name="test", location_id_name="id", gazetteer_id=uuid.uuid4())

        # Assert
        assert hasattr(source, "features")

    def test_has_unique_constraint_on_gazetteer_and_name(
        self, test_session: Session, gazetteer_factory
    ):
        """Test that Source has unique constraint on (gazetteer_id, name)."""
        # Arrange
        from sqlalchemy.exc import IntegrityError

        from geoparser.db.models import Source

        gazetteer = gazetteer_factory()
        source1 = Source(
            name="test_source", location_id_name="id", gazetteer_id=gazetteer.id
        )
        test_session.add(source1)
        test_session.commit()

        # Act & Assert - Try to create duplicate
        source2 = Source(
            name="test_source", location_id_name="id2", gazetteer_id=gazetteer.id
        )
        test_session.add(source2)

        with pytest.raises(IntegrityError):
            test_session.commit()

    def test_str_representation(self, test_session: Session):
        """Test that Source has a useful string representation."""
        # Arrange
        from geoparser.db.models import Source

        source = Source(
            name="geonames_main", location_id_name="id", gazetteer_id=uuid.uuid4()
        )

        # Act
        str_repr = str(source)

        # Assert
        assert "Source" in str_repr
        assert "geonames_main" in str_repr

    def test_repr_matches_str(self, test_session: Session):
        """Test that __repr__ matches __str__."""
        # Arrange
        from geoparser.db.models import Source

        source = Source(name="test", location_id_name="id", gazetteer_id=uuid.uuid4())

        # Act & Assert
        assert repr(source) == str(source)


@pytest.mark.unit
class TestSourceCreate:
    """Test the SourceCreate model."""

    def test_creates_with_required_fields(self):
        """Test that SourceCreate can be created with required fields."""
        # Arrange
        gazetteer_id = uuid.uuid4()

        # Act
        source_create = SourceCreate(
            name="geonames_main",
            location_id_name="geonameid",
            gazetteer_id=gazetteer_id,
        )

        # Assert
        assert source_create.name == "geonames_main"
        assert source_create.location_id_name == "geonameid"
        assert source_create.gazetteer_id == gazetteer_id


@pytest.mark.unit
class TestSourceUpdate:
    """Test the SourceUpdate model."""

    def test_creates_update_with_all_fields(self):
        """Test that SourceUpdate can be created with all fields."""
        # Arrange
        gazetteer_id = uuid.uuid4()

        # Act
        source_update = SourceUpdate(
            id=1,
            name="Updated Name",
            location_id_name="new_id",
            gazetteer_id=gazetteer_id,
        )

        # Assert
        assert source_update.id == 1
        assert source_update.name == "Updated Name"
        assert source_update.location_id_name == "new_id"
        assert source_update.gazetteer_id == gazetteer_id

    def test_allows_optional_fields(self):
        """Test that SourceUpdate allows optional fields."""
        # Arrange & Act
        source_update = SourceUpdate(id=1)

        # Assert
        assert source_update.id == 1
        assert source_update.name is None
        assert source_update.location_id_name is None
        assert source_update.gazetteer_id is None
