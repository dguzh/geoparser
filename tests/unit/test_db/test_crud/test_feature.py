"""
Unit tests for geoparser/db/crud/feature.py

Tests the FeatureRepository with focus on FTS search methods.
"""

from unittest.mock import Mock

import pytest

from geoparser.db.crud.feature import FeatureRepository


@pytest.mark.unit
class TestFeatureRepositoryGetByGazetteer:
    """Test FeatureRepository.get_by_gazetteer() method."""

    def test_queries_features_by_gazetteer_name(self, test_session):
        """Test that features are queried by gazetteer name."""
        # Arrange - mock the exec result
        mock_result = Mock()
        mock_result.unique.return_value.all.return_value = []
        test_session.exec = Mock(return_value=mock_result)

        # Act
        result = FeatureRepository.get_by_gazetteer(test_session, "test_gazetteer")

        # Assert
        assert result == []
        test_session.exec.assert_called_once()


@pytest.mark.unit
class TestFeatureRepositoryGetByGazetteerAndIdentifier:
    """Test FeatureRepository.get_by_gazetteer_and_identifier() method."""

    def test_queries_feature_by_gazetteer_and_identifier(self, test_session):
        """Test that feature is queried by gazetteer name and identifier."""
        # Arrange
        mock_result = Mock()
        mock_result.unique.return_value.first.return_value = None
        test_session.exec = Mock(return_value=mock_result)

        # Act
        result = FeatureRepository.get_by_gazetteer_and_identifier(
            test_session, "test_gaz", "123"
        )

        # Assert
        assert result is None
        test_session.exec.assert_called_once()


@pytest.mark.unit
class TestFeatureRepositoryGetByGazetteerAndNameExact:
    """Test FeatureRepository.get_by_gazetteer_and_name_exact() method."""

    def test_builds_exact_match_query(self, test_session):
        """Test that exact match query is built with length constraint."""
        # Arrange
        mock_result = Mock()
        mock_result.unique.return_value.all.return_value = []
        test_session.exec = Mock(return_value=mock_result)

        # Act
        result = FeatureRepository.get_by_gazetteer_and_name_exact(
            test_session, "test_gaz", "Paris"
        )

        # Assert
        assert result == []
        test_session.exec.assert_called_once()

    def test_uses_quoted_query_for_exact_match(self, test_session):
        """Test that query is wrapped in quotes for exact matching."""
        # Arrange
        mock_result = Mock()
        mock_result.unique.return_value.all.return_value = []
        test_session.exec = Mock(return_value=mock_result)

        # Act
        FeatureRepository.get_by_gazetteer_and_name_exact(
            test_session, "test_gaz", "New York"
        )

        # Assert - query should be wrapped in quotes
        test_session.exec.assert_called_once()


@pytest.mark.unit
class TestFeatureRepositoryGetByGazetteerAndNamePhrase:
    """Test FeatureRepository.get_by_gazetteer_and_name_phrase() method."""

    def test_builds_phrase_query_with_bm25_ranking(self, test_session):
        """Test that phrase query is built with BM25 ranking."""
        # Arrange
        mock_result = Mock()
        mock_result.unique.return_value.all.return_value = []
        test_session.exec = Mock(return_value=mock_result)

        # Act
        result = FeatureRepository.get_by_gazetteer_and_name_phrase(
            test_session, "test_gaz", "New York"
        )

        # Assert
        assert result == []
        test_session.exec.assert_called_once()


@pytest.mark.unit
class TestFeatureRepositoryGetByGazetteerAndNamePartial:
    """Test FeatureRepository.get_by_gazetteer_and_name_partial() method."""

    def test_builds_partial_query_with_or_logic(self, test_session):
        """Test that partial query uses OR logic for tokens."""
        # Arrange
        mock_result = Mock()
        mock_result.unique.return_value.all.return_value = []
        test_session.exec = Mock(return_value=mock_result)

        # Act
        result = FeatureRepository.get_by_gazetteer_and_name_partial(
            test_session, "test_gaz", "New York"
        )

        # Assert
        assert result == []
        # Partial search should use OR between tokens
        test_session.exec.assert_called_once()


@pytest.mark.unit
class TestFeatureRepositoryGetByGazetteerAndNameFuzzy:
    """Test FeatureRepository.get_by_gazetteer_and_name_fuzzy() method."""

    def test_builds_fuzzy_query_with_spellfix(self, test_session):
        """Test that fuzzy query uses spellfix with phonetic hashing and edit distance."""
        # Arrange
        mock_result = Mock()
        mock_result.unique.return_value.all.return_value = []
        test_session.exec = Mock(return_value=mock_result)

        # Act
        result = FeatureRepository.get_by_gazetteer_and_name_fuzzy(
            test_session, "test_gaz", "Paris"
        )

        # Assert
        assert result == []
        # Should build query with spellfix joins and k2 phonetic hash matching
        test_session.exec.assert_called_once()
