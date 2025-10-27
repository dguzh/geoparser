"""
Unit tests for geoparser/db/models/referent.py

Tests the Referent model.
"""

import uuid

import pytest
from sqlmodel import Session

from geoparser.db.models import ReferentCreate, ReferentUpdate


@pytest.mark.unit
class TestReferentModel:
    """Test the Referent model."""

    def test_creates_referent_with_valid_data(
        self,
        test_session: Session,
        reference_factory,
        resolver_factory,
        feature_factory,
    ):
        """Test that a Referent can be created with valid data."""
        # Arrange
        from geoparser.db.models import Referent

        # Create feature hierarchy
        feature = feature_factory()
        reference = reference_factory()
        resolver = resolver_factory(id="test_resolver")

        referent = Referent(
            reference_id=reference.id,
            feature_id=feature.id,
            resolver_id=resolver.id,
        )

        # Act
        test_session.add(referent)
        test_session.commit()
        test_session.refresh(referent)

        # Assert
        assert referent.id is not None
        assert isinstance(referent.id, uuid.UUID)
        assert referent.reference_id == reference.id
        assert referent.feature_id == feature.id
        assert referent.resolver_id == resolver.id

    def test_generates_uuid_automatically(
        self,
        test_session: Session,
        reference_factory,
        resolver_factory,
        feature_factory,
    ):
        """Test that Referent automatically generates a UUID for id."""
        # Arrange
        from geoparser.db.models import Referent

        # Create feature hierarchy
        feature = feature_factory()
        reference = reference_factory()
        resolver = resolver_factory(id="test")

        referent = Referent(
            reference_id=reference.id, feature_id=feature.id, resolver_id=resolver.id
        )

        # Act
        test_session.add(referent)
        test_session.commit()

        # Assert
        assert referent.id is not None
        assert isinstance(referent.id, uuid.UUID)

    def test_has_reference_relationship(self, test_session: Session):
        """Test that Referent has a relationship to reference."""
        # Arrange
        from geoparser.db.models import Referent

        referent = Referent(reference_id=uuid.uuid4(), feature_id=1, resolver_id="test")

        # Assert
        assert hasattr(referent, "reference")

    def test_has_resolver_relationship(self, test_session: Session):
        """Test that Referent has a relationship to resolver."""
        # Arrange
        from geoparser.db.models import Referent

        referent = Referent(reference_id=uuid.uuid4(), feature_id=1, resolver_id="test")

        # Assert
        assert hasattr(referent, "resolver")

    def test_has_feature_relationship(self, test_session: Session):
        """Test that Referent has a relationship to feature."""
        # Arrange
        from geoparser.db.models import Referent

        referent = Referent(reference_id=uuid.uuid4(), feature_id=1, resolver_id="test")

        # Assert
        assert hasattr(referent, "feature")


@pytest.mark.unit
class TestReferentCreate:
    """Test the ReferentCreate model."""

    def test_creates_with_required_fields(self):
        """Test that ReferentCreate can be created with required fields."""
        # Arrange
        reference_id = uuid.uuid4()
        feature_id = 123
        resolver_id = "test_resolver"

        # Act
        referent_create = ReferentCreate(
            reference_id=reference_id,
            feature_id=feature_id,
            resolver_id=resolver_id,
        )

        # Assert
        assert referent_create.reference_id == reference_id
        assert referent_create.feature_id == feature_id
        assert referent_create.resolver_id == resolver_id


@pytest.mark.unit
class TestReferentUpdate:
    """Test the ReferentUpdate model."""

    def test_creates_update_with_all_fields(self):
        """Test that ReferentUpdate can be created with all fields."""
        # Arrange
        referent_id = uuid.uuid4()
        reference_id = uuid.uuid4()

        # Act
        referent_update = ReferentUpdate(
            id=referent_id,
            reference_id=reference_id,
            feature_id=456,
            resolver_id="new_resolver",
        )

        # Assert
        assert referent_update.id == referent_id
        assert referent_update.reference_id == reference_id
        assert referent_update.feature_id == 456
        assert referent_update.resolver_id == "new_resolver"

    def test_allows_optional_fields(self):
        """Test that ReferentUpdate allows optional fields."""
        # Arrange
        referent_id = uuid.uuid4()

        # Act
        referent_update = ReferentUpdate(id=referent_id)

        # Assert
        assert referent_update.id == referent_id
        assert referent_update.reference_id is None
        assert referent_update.feature_id is None
        assert referent_update.resolver_id is None
