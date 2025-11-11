"""
Unit tests for geoparser/db/crud/gazetteer.py

Tests the GazetteerRepository class with custom query methods.
"""

import pytest
from sqlmodel import Session

from geoparser.db.crud import GazetteerRepository


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
        gazetteer = gazetteer_factory(name="geonames")

        # Act
        found_gazetteer = GazetteerRepository.get_by_name(test_session, "wikidata")

        # Assert
        assert found_gazetteer is None

    def test_returns_correct_gazetteer_when_multiple_exist(
        self, test_session: Session, gazetteer_factory
    ):
        """Test that get_by_name returns correct gazetteer when multiple exist."""
        # Arrange
        gaz1 = gazetteer_factory(name="geonames")
        gaz2 = gazetteer_factory(name="wikidata")

        # Act
        found_gazetteer = GazetteerRepository.get_by_name(test_session, "wikidata")

        # Assert
        assert found_gazetteer is not None
        assert found_gazetteer.id == gaz2.id
        assert found_gazetteer.name == "wikidata"
