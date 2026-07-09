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
    ):
        """Test that a Referent can be created with valid data."""
        # Arrange
        from geoparser.db.models import Referent

        reference = reference_factory()
        resolver = resolver_factory(id="test_resolver")

        referent = Referent(
            reference_id=reference.id,
            gazetteer_name="andorranames",
            feature_identifier="3041563",
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
        assert referent.gazetteer_name == "andorranames"
        assert referent.feature_identifier == "3041563"
        assert referent.resolver_id == resolver.id

    def test_generates_uuid_automatically(
        self,
        test_session: Session,
        reference_factory,
        resolver_factory,
    ):
        """Test that Referent automatically generates a UUID for id."""
        # Arrange
        from geoparser.db.models import Referent

        reference = reference_factory()
        resolver = resolver_factory(id="test")

        referent = Referent(
            reference_id=reference.id,
            gazetteer_name="andorranames",
            feature_identifier="3041563",
            resolver_id=resolver.id,
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

        referent = Referent(
            reference_id=uuid.uuid4(),
            gazetteer_name="andorranames",
            feature_identifier="1",
            resolver_id="test",
        )

        # Assert
        assert hasattr(referent, "reference")

    def test_has_resolver_relationship(self, test_session: Session):
        """Test that Referent has a relationship to resolver."""
        # Arrange
        from geoparser.db.models import Referent

        referent = Referent(
            reference_id=uuid.uuid4(),
            gazetteer_name="andorranames",
            feature_identifier="1",
            resolver_id="test",
        )

        # Assert
        assert hasattr(referent, "resolver")

    def test_feature_property_resolves_through_gazetteer(self, test_session: Session):
        """Test that Referent.feature looks the feature up in its gazetteer."""
        from unittest.mock import Mock, patch

        from geoparser.db.models import Referent

        referent = Referent(
            reference_id=uuid.uuid4(),
            gazetteer_name="andorranames",
            feature_identifier="3041563",
            resolver_id="test",
        )
        fake_feature = Mock()

        with patch("geoparser.gazetteer.gazetteer.Gazetteer") as mock_gazetteer:
            mock_gazetteer.return_value.find.return_value = fake_feature

            feature = referent.feature

        mock_gazetteer.assert_called_once_with("andorranames")
        mock_gazetteer.return_value.find.assert_called_once_with("3041563")
        assert feature is fake_feature


@pytest.mark.unit
class TestReferentCreate:
    """Test the ReferentCreate model."""

    def test_creates_with_required_fields(self):
        """Test that ReferentCreate can be created with required fields."""
        # Arrange
        reference_id = uuid.uuid4()
        resolver_id = "test_resolver"

        # Act
        referent_create = ReferentCreate(
            reference_id=reference_id,
            gazetteer_name="andorranames",
            feature_identifier="123",
            resolver_id=resolver_id,
        )

        # Assert
        assert referent_create.reference_id == reference_id
        assert referent_create.gazetteer_name == "andorranames"
        assert referent_create.feature_identifier == "123"
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
            gazetteer_name="geonames",
            feature_identifier="456",
            resolver_id="new_resolver",
        )

        # Assert
        assert referent_update.id == referent_id
        assert referent_update.reference_id == reference_id
        assert referent_update.gazetteer_name == "geonames"
        assert referent_update.feature_identifier == "456"
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
        assert referent_update.gazetteer_name is None
        assert referent_update.feature_identifier is None
        assert referent_update.resolver_id is None
