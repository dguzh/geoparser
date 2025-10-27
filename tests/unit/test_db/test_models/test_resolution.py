"""
Unit tests for geoparser/db/models/resolution.py

Tests the Resolution model.
"""

import uuid

import pytest
from sqlmodel import Session

from geoparser.db.models import ResolutionCreate, ResolutionUpdate


@pytest.mark.unit
class TestResolutionModel:
    """Test the Resolution model."""

    def test_creates_resolution_with_valid_data(
        self, test_session: Session, reference_factory, resolver_factory
    ):
        """Test that a Resolution can be created with valid data."""
        # Arrange
        from geoparser.db.models import Resolution

        reference = reference_factory()
        resolver = resolver_factory(id="test_resolver")

        resolution = Resolution(reference_id=reference.id, resolver_id=resolver.id)

        # Act
        test_session.add(resolution)
        test_session.commit()
        test_session.refresh(resolution)

        # Assert
        assert resolution.id is not None
        assert isinstance(resolution.id, uuid.UUID)
        assert resolution.reference_id == reference.id
        assert resolution.resolver_id == resolver.id

    def test_generates_uuid_automatically(
        self, test_session: Session, reference_factory, resolver_factory
    ):
        """Test that Resolution automatically generates a UUID for id."""
        # Arrange
        from geoparser.db.models import Resolution

        reference = reference_factory()
        resolver = resolver_factory(id="test")

        resolution = Resolution(reference_id=reference.id, resolver_id=resolver.id)

        # Act
        test_session.add(resolution)
        test_session.commit()

        # Assert
        assert resolution.id is not None
        assert isinstance(resolution.id, uuid.UUID)

    def test_has_reference_relationship(self, test_session: Session):
        """Test that Resolution has a relationship to reference."""
        # Arrange
        from geoparser.db.models import Resolution

        resolution = Resolution(reference_id=uuid.uuid4(), resolver_id="test")

        # Assert
        assert hasattr(resolution, "reference")

    def test_has_resolver_relationship(self, test_session: Session):
        """Test that Resolution has a relationship to resolver."""
        # Arrange
        from geoparser.db.models import Resolution

        resolution = Resolution(reference_id=uuid.uuid4(), resolver_id="test")

        # Assert
        assert hasattr(resolution, "resolver")


@pytest.mark.unit
class TestResolutionCreate:
    """Test the ResolutionCreate model."""

    def test_creates_with_required_fields(self):
        """Test that ResolutionCreate can be created with required fields."""
        # Arrange
        reference_id = uuid.uuid4()
        resolver_id = "test_resolver"

        # Act
        resolution_create = ResolutionCreate(
            reference_id=reference_id, resolver_id=resolver_id
        )

        # Assert
        assert resolution_create.reference_id == reference_id
        assert resolution_create.resolver_id == resolver_id


@pytest.mark.unit
class TestResolutionUpdate:
    """Test the ResolutionUpdate model."""

    def test_creates_update_with_all_fields(self):
        """Test that ResolutionUpdate can be created with all fields."""
        # Arrange
        resolution_id = uuid.uuid4()
        reference_id = uuid.uuid4()

        # Act
        resolution_update = ResolutionUpdate(
            id=resolution_id,
            reference_id=reference_id,
            resolver_id="new_resolver",
        )

        # Assert
        assert resolution_update.id == resolution_id
        assert resolution_update.reference_id == reference_id
        assert resolution_update.resolver_id == "new_resolver"

    def test_allows_optional_fields(self):
        """Test that ResolutionUpdate allows optional fields."""
        # Arrange
        resolution_id = uuid.uuid4()

        # Act
        resolution_update = ResolutionUpdate(id=resolution_id)

        # Assert
        assert resolution_update.id == resolution_id
        assert resolution_update.reference_id is None
        assert resolution_update.resolver_id is None
