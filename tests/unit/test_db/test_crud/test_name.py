"""
Unit tests for geoparser/db/crud/name.py

Tests the NameRepository class with custom query methods.
"""

import pytest
from sqlmodel import Session

from geoparser.db.crud import NameRepository


@pytest.mark.unit
class TestNameRepositoryGetByFeature:
    """Test the get_by_feature method of NameRepository."""

    def test_returns_names_for_feature(
        self, test_session: Session, feature_factory, name_factory
    ):
        """Test that get_by_feature returns all names for a feature."""
        # Arrange
        feature = feature_factory()
        name1 = name_factory(text="Paris", feature_id=feature.id)
        name2 = name_factory(text="Paree", feature_id=feature.id)

        # Act
        names = NameRepository.get_by_feature(test_session, feature.id)

        # Assert
        assert len(names) == 2
        name_ids = [n.id for n in names]
        assert name1.id in name_ids
        assert name2.id in name_ids

    def test_returns_empty_list_for_feature_without_names(
        self, test_session: Session, feature_factory
    ):
        """Test that get_by_feature returns empty list for feature without names."""
        # Arrange
        feature = feature_factory()

        # Act
        names = NameRepository.get_by_feature(test_session, feature.id)

        # Assert
        assert names == []

    def test_filters_by_feature(
        self, test_session: Session, feature_factory, name_factory
    ):
        """Test that get_by_feature only returns names from specified feature."""
        # Arrange
        feature1 = feature_factory()
        feature2 = feature_factory()

        name1 = name_factory(text="Name in Feature 1", feature_id=feature1.id)
        name2 = name_factory(text="Name in Feature 2", feature_id=feature2.id)

        # Act
        names = NameRepository.get_by_feature(test_session, feature1.id)

        # Assert
        assert len(names) == 1
        assert names[0].id == name1.id
        assert names[0].text == "Name in Feature 1"


@pytest.mark.unit
class TestNameRepositoryGetByName:
    """Test the get_by_name method of NameRepository."""

    def test_returns_names_for_matching_text(
        self, test_session: Session, feature_factory, name_factory
    ):
        """Test that get_by_name returns all names matching the text."""
        # Arrange
        feature1 = feature_factory()
        feature2 = feature_factory()

        name1 = name_factory(text="Paris", feature_id=feature1.id)
        name2 = name_factory(text="Paris", feature_id=feature2.id)

        # Act
        names = NameRepository.get_by_name(test_session, "Paris")

        # Assert
        assert len(names) == 2
        name_ids = [n.id for n in names]
        assert name1.id in name_ids
        assert name2.id in name_ids

    def test_returns_empty_list_for_non_matching_text(
        self, test_session: Session, name_factory
    ):
        """Test that get_by_name returns empty list when text doesn't match."""
        # Arrange
        name = name_factory(text="Paris")

        # Act
        names = NameRepository.get_by_name(test_session, "London")

        # Assert
        assert names == []
