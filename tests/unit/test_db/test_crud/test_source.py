"""
Unit tests for geoparser/db/crud/source.py

Tests the SourceRepository class with custom query methods.
"""

import pytest
from sqlmodel import Session

from geoparser.db.crud import SourceRepository


@pytest.mark.unit
class TestSourceRepositoryGetByGazetteer:
    """Test the get_by_gazetteer method of SourceRepository."""

    def test_returns_sources_for_gazetteer(
        self, test_session: Session, gazetteer_factory, source_factory
    ):
        """Test that get_by_gazetteer returns all sources for a gazetteer."""
        # Arrange
        gazetteer = gazetteer_factory()
        source1 = source_factory(name="source1", gazetteer_id=gazetteer.id)
        source2 = source_factory(name="source2", gazetteer_id=gazetteer.id)

        # Act
        sources = SourceRepository.get_by_gazetteer(test_session, gazetteer.id)

        # Assert
        assert len(sources) == 2
        source_ids = [s.id for s in sources]
        assert source1.id in source_ids
        assert source2.id in source_ids

    def test_returns_empty_list_for_gazetteer_without_sources(
        self, test_session: Session, gazetteer_factory
    ):
        """Test that get_by_gazetteer returns empty list for gazetteer without sources."""
        # Arrange
        gazetteer = gazetteer_factory()

        # Act
        sources = SourceRepository.get_by_gazetteer(test_session, gazetteer.id)

        # Assert
        assert sources == []

    def test_filters_by_gazetteer(
        self, test_session: Session, gazetteer_factory, source_factory
    ):
        """Test that get_by_gazetteer only returns sources from specified gazetteer."""
        # Arrange
        gaz1 = gazetteer_factory(name="Gazetteer 1")
        gaz2 = gazetteer_factory(name="Gazetteer 2")

        source1 = source_factory(name="Source in Gaz 1", gazetteer_id=gaz1.id)
        source2 = source_factory(name="Source in Gaz 2", gazetteer_id=gaz2.id)

        # Act
        sources = SourceRepository.get_by_gazetteer(test_session, gaz1.id)

        # Assert
        assert len(sources) == 1
        assert sources[0].id == source1.id
        assert sources[0].name == "Source in Gaz 1"


@pytest.mark.unit
class TestSourceRepositoryGetByGazetteerAndName:
    """Test the get_by_gazetteer_and_name method of SourceRepository."""

    def test_returns_source_for_matching_gazetteer_and_name(
        self, test_session: Session, gazetteer_factory, source_factory
    ):
        """Test that get_by_gazetteer_and_name returns source when both match."""
        # Arrange
        gazetteer = gazetteer_factory(name="geonames")
        source = source_factory(name="main", gazetteer_id=gazetteer.id)

        # Act
        found_source = SourceRepository.get_by_gazetteer_and_name(
            test_session, gazetteer.id, "main"
        )

        # Assert
        assert found_source is not None
        assert found_source.id == source.id
        assert found_source.name == "main"

    def test_returns_none_for_non_matching_name(
        self, test_session: Session, gazetteer_factory, source_factory
    ):
        """Test that get_by_gazetteer_and_name returns None when name doesn't match."""
        # Arrange
        gazetteer = gazetteer_factory()
        source = source_factory(name="main", gazetteer_id=gazetteer.id)

        # Act
        found_source = SourceRepository.get_by_gazetteer_and_name(
            test_session, gazetteer.id, "alternate"
        )

        # Assert
        assert found_source is None

    def test_returns_none_for_non_matching_gazetteer(
        self, test_session: Session, gazetteer_factory, source_factory
    ):
        """Test that get_by_gazetteer_and_name returns None when gazetteer doesn't match."""
        # Arrange
        gaz1 = gazetteer_factory(name="geonames")
        gaz2 = gazetteer_factory(name="wikidata")
        source = source_factory(name="main", gazetteer_id=gaz1.id)

        # Act
        found_source = SourceRepository.get_by_gazetteer_and_name(
            test_session, gaz2.id, "main"
        )

        # Assert
        assert found_source is None

    def test_distinguishes_between_same_name_different_gazetteers(
        self, test_session: Session, gazetteer_factory, source_factory
    ):
        """Test that method can distinguish sources with same name in different gazetteers."""
        # Arrange
        gaz1 = gazetteer_factory(name="geonames")
        gaz2 = gazetteer_factory(name="wikidata")

        source1 = source_factory(name="main", gazetteer_id=gaz1.id)
        source2 = source_factory(name="main", gazetteer_id=gaz2.id)

        # Act
        found_source1 = SourceRepository.get_by_gazetteer_and_name(
            test_session, gaz1.id, "main"
        )
        found_source2 = SourceRepository.get_by_gazetteer_and_name(
            test_session, gaz2.id, "main"
        )

        # Assert
        assert found_source1 is not None
        assert found_source2 is not None
        assert found_source1.id == source1.id
        assert found_source2.id == source2.id
        assert found_source1.id != found_source2.id
