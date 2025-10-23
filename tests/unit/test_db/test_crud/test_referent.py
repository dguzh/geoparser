"""
Unit tests for geoparser/db/crud/referent.py

Tests the ReferentRepository class with custom query methods.
"""

import pytest
from sqlmodel import Session

from geoparser.db.crud import ReferentRepository
from geoparser.db.models import ReferentCreate


@pytest.mark.unit
class TestReferentRepositoryGetByReference:
    """Test the get_by_reference method of ReferentRepository."""

    def test_returns_referents_for_reference(
        self,
        test_session: Session,
        reference_factory,
        resolver_factory,
        feature_factory,
    ):
        """Test that get_by_reference returns all referents for a reference."""
        # Arrange
        reference = reference_factory()
        resolver1 = resolver_factory(id="res1")
        resolver2 = resolver_factory(id="res2")
        feature1 = feature_factory()
        feature2 = feature_factory()

        ref1 = ReferentRepository.create(
            test_session,
            ReferentCreate(
                reference_id=reference.id, feature_id=feature1.id, resolver_id="res1"
            ),
        )
        ref2 = ReferentRepository.create(
            test_session,
            ReferentCreate(
                reference_id=reference.id, feature_id=feature2.id, resolver_id="res2"
            ),
        )

        # Act
        referents = ReferentRepository.get_by_reference(test_session, reference.id)

        # Assert
        assert len(referents) == 2
        referent_ids = [r.id for r in referents]
        assert ref1.id in referent_ids
        assert ref2.id in referent_ids

    def test_returns_empty_list_for_reference_without_referents(
        self, test_session: Session, reference_factory
    ):
        """Test that get_by_reference returns empty list for reference without referents."""
        # Arrange
        reference = reference_factory()

        # Act
        referents = ReferentRepository.get_by_reference(test_session, reference.id)

        # Assert
        assert referents == []

    def test_filters_by_reference(
        self,
        test_session: Session,
        reference_factory,
        resolver_factory,
        feature_factory,
    ):
        """Test that get_by_reference only returns referents from specified reference."""
        # Arrange
        ref1 = reference_factory()
        ref2 = reference_factory()
        resolver = resolver_factory(id="test_res")
        feature1 = feature_factory()
        feature2 = feature_factory()

        referent1 = ReferentRepository.create(
            test_session,
            ReferentCreate(
                reference_id=ref1.id, feature_id=feature1.id, resolver_id="test_res"
            ),
        )
        referent2 = ReferentRepository.create(
            test_session,
            ReferentCreate(
                reference_id=ref2.id, feature_id=feature2.id, resolver_id="test_res"
            ),
        )

        # Act
        referents = ReferentRepository.get_by_reference(test_session, ref1.id)

        # Assert
        assert len(referents) == 1
        assert referents[0].id == referent1.id
