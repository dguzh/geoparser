"""
Unit tests for geoparser/db/crud/gazetteer.py

Tests the GazetteerRepository class with custom query methods.
"""

from datetime import datetime, timezone

import pytest
from sqlmodel import Session

from geoparser.db.crud import GazetteerRepository
from geoparser.db.models import GazetteerUpdate


@pytest.mark.unit
class TestGazetteerRepositoryGetByName:
    """Test the get_by_name method of GazetteerRepository."""

    def test_returns_gazetteer_for_matching_name(
        self, test_session: Session, gazetteer_factory
    ):
        """Test that get_by_name returns gazetteer when name matches."""
        # Arrange
        gazetteer = gazetteer_factory(name="geonames")

        # Act
        found_gazetteer = GazetteerRepository.get_by_name(test_session, "geonames")

        # Assert
        assert found_gazetteer is not None
        assert found_gazetteer.id == gazetteer.id
        assert found_gazetteer.name == "geonames"

    def test_returns_none_for_non_matching_name(
        self, test_session: Session, gazetteer_factory
    ):
        """Test that get_by_name returns None when name doesn't match."""
        # Arrange
        gazetteer_factory(name="geonames")

        # Act
        found_gazetteer = GazetteerRepository.get_by_name(test_session, "wikidata")

        # Assert
        assert found_gazetteer is None

    def test_returns_correct_gazetteer_when_multiple_exist(
        self, test_session: Session, gazetteer_factory
    ):
        """Test that get_by_name returns correct gazetteer when multiple exist."""
        # Arrange
        gazetteer_factory(name="geonames")
        gaz2 = gazetteer_factory(name="wikidata")

        # Act
        found_gazetteer = GazetteerRepository.get_by_name(test_session, "wikidata")

        # Assert
        assert found_gazetteer is not None
        assert found_gazetteer.id == gaz2.id
        assert found_gazetteer.name == "wikidata"


@pytest.mark.unit
class TestGazetteerRepositoryInstalledAt:
    """Test installation state via get_by_name and update."""

    def test_installed_at_none_by_default(
        self, test_session: Session, gazetteer_factory
    ):
        """Test that a new gazetteer record is not marked as installed."""
        gazetteer_record = gazetteer_factory(name="geonames")

        assert gazetteer_record.installed_at is None

    def test_update_sets_installed_at(self, test_session: Session, gazetteer_factory):
        """Test that installed_at can be set through the standard update path."""
        gazetteer_record = gazetteer_factory(name="geonames")
        installed_at = datetime.now(timezone.utc)
        gazetteer_update = GazetteerUpdate(
            id=gazetteer_record.id, installed_at=installed_at
        )

        updated_gazetteer_record = GazetteerRepository.update(
            test_session, db_obj=gazetteer_record, obj_in=gazetteer_update
        )

        assert updated_gazetteer_record.installed_at is not None

    def test_update_clears_installed_at(self, test_session: Session, gazetteer_factory):
        """Test that installed_at can be cleared through the standard update path."""
        gazetteer_record = gazetteer_factory(name="geonames")
        gazetteer_update = GazetteerUpdate(
            id=gazetteer_record.id, installed_at=datetime.now(timezone.utc)
        )
        GazetteerRepository.update(
            test_session, db_obj=gazetteer_record, obj_in=gazetteer_update
        )

        gazetteer_update = GazetteerUpdate(id=gazetteer_record.id, installed_at=None)
        updated_gazetteer_record = GazetteerRepository.update(
            test_session, db_obj=gazetteer_record, obj_in=gazetteer_update
        )

        assert updated_gazetteer_record.installed_at is None
