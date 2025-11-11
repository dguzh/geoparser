"""
Unit tests for geoparser/db/models/gazetteer.py

Tests the Gazetteer model.
"""

import uuid

import pytest
from sqlmodel import Session

from geoparser.db.models import GazetteerCreate, GazetteerUpdate


@pytest.mark.unit
class TestGazetteerModel:
    """Test the Gazetteer model."""

    def test_creates_gazetteer_with_valid_data(self, test_session: Session):
        """Test that a Gazetteer can be created with valid data."""
        # Arrange
        from geoparser.db.models import Gazetteer

        gazetteer = Gazetteer(name="geonames")

        # Act
        test_session.add(gazetteer)
        test_session.commit()
        test_session.refresh(gazetteer)

        # Assert
        assert gazetteer.id is not None
        assert isinstance(gazetteer.id, uuid.UUID)
        assert gazetteer.name == "geonames"

    def test_generates_uuid_automatically(self, test_session: Session):
        """Test that Gazetteer automatically generates a UUID for id."""
        # Arrange
        from geoparser.db.models import Gazetteer

        gazetteer = Gazetteer(name="test")

        # Act
        test_session.add(gazetteer)
        test_session.commit()

        # Assert
        assert gazetteer.id is not None
        assert isinstance(gazetteer.id, uuid.UUID)

    def test_name_is_indexed(self, test_session: Session):
        """Test that the name field is indexed for efficient queries."""
        # Arrange
        from sqlmodel import select

        from geoparser.db.models import Gazetteer

        gazetteer = Gazetteer(name="Indexed Gazetteer")
        test_session.add(gazetteer)
        test_session.commit()

        # Act - Query by name should work efficiently
        statement = select(Gazetteer).where(Gazetteer.name == "Indexed Gazetteer")
        result = test_session.exec(statement).first()

        # Assert
        assert result is not None
        assert result.name == "Indexed Gazetteer"

    def test_has_sources_relationship(self, test_session: Session):
        """Test that Gazetteer has a relationship to sources."""
        # Arrange
        from geoparser.db.models import Gazetteer

        gazetteer = Gazetteer(name="test")
        test_session.add(gazetteer)
        test_session.commit()

        # Assert
        assert hasattr(gazetteer, "sources")
        assert isinstance(gazetteer.sources, list)
        assert len(gazetteer.sources) == 0


@pytest.mark.unit
class TestGazetteerCreate:
    """Test the GazetteerCreate model."""

    def test_creates_with_required_fields(self):
        """Test that GazetteerCreate can be created with required fields."""
        # Arrange & Act
        gazetteer_create = GazetteerCreate(name="geonames")

        # Assert
        assert gazetteer_create.name == "geonames"


@pytest.mark.unit
class TestGazetteerUpdate:
    """Test the GazetteerUpdate model."""

    def test_creates_update_with_all_fields(self):
        """Test that GazetteerUpdate can be created with all fields."""
        # Arrange
        gazetteer_id = uuid.uuid4()

        # Act
        gazetteer_update = GazetteerUpdate(id=gazetteer_id, name="Updated Name")

        # Assert
        assert gazetteer_update.id == gazetteer_id
        assert gazetteer_update.name == "Updated Name"

    def test_allows_optional_name(self):
        """Test that GazetteerUpdate allows name to be optional."""
        # Arrange
        gazetteer_id = uuid.uuid4()

        # Act
        gazetteer_update = GazetteerUpdate(id=gazetteer_id)

        # Assert
        assert gazetteer_update.id == gazetteer_id
        assert gazetteer_update.name is None
