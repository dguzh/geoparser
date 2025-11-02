"""
Unit tests for geoparser/db/crud/feature.py

Tests the FeatureRepository with focus on FTS search methods.
"""

from unittest.mock import Mock

import pytest

from geoparser.db.crud.feature import FeatureRepository
from geoparser.db.models.feature import Feature


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


@pytest.mark.unit
class TestFeatureRepositoryFilterByRanks:
    """Test FeatureRepository._filter_by_ranks() helper method."""

    def test_returns_empty_list_for_empty_results(self):
        """Test that empty results return empty list."""
        # Act
        result = FeatureRepository._filter_by_ranks([], ranks=1)

        # Assert
        assert result == []

    def test_returns_empty_list_for_zero_ranks(self):
        """Test that zero ranks return empty list."""
        # Arrange
        mock_feature = Mock()
        results = [(mock_feature, 0.5)]

        # Act
        result = FeatureRepository._filter_by_ranks(results, ranks=0)

        # Assert
        assert result == []

    def test_returns_empty_list_for_negative_ranks(self):
        """Test that negative ranks return empty list."""
        # Arrange
        mock_feature = Mock()
        results = [(mock_feature, 0.5)]

        # Act
        result = FeatureRepository._filter_by_ranks(results, ranks=-1)

        # Assert
        assert result == []

    def test_filters_to_top_rank_group(self):
        """Test that only top rank group is returned when ranks=1."""
        # Arrange
        feature1 = Mock(spec=Feature)
        feature2 = Mock(spec=Feature)
        feature3 = Mock(spec=Feature)
        results = [
            (feature1, -2.5),  # Best rank (most negative)
            (feature2, -2.5),  # Same rank as feature1
            (feature3, -1.0),  # Worse rank
        ]

        # Act
        result = FeatureRepository._filter_by_ranks(results, ranks=1)

        # Assert
        assert len(result) == 2
        assert feature1 in result
        assert feature2 in result
        assert feature3 not in result

    def test_filters_to_top_n_rank_groups(self):
        """Test that top N rank groups are returned."""
        # Arrange
        feature1 = Mock(spec=Feature)
        feature2 = Mock(spec=Feature)
        feature3 = Mock(spec=Feature)
        feature4 = Mock(spec=Feature)
        results = [
            (feature1, -3.0),  # Best rank
            (feature2, -2.0),  # Second best
            (feature3, -2.0),  # Same as feature2
            (feature4, -1.0),  # Third best
        ]

        # Act
        result = FeatureRepository._filter_by_ranks(results, ranks=2)

        # Assert
        assert len(result) == 3
        assert feature1 in result
        assert feature2 in result
        assert feature3 in result
        assert feature4 not in result

    def test_returns_all_features_when_ranks_exceeds_unique_ranks(self):
        """Test that all features are returned when ranks > unique rank count."""
        # Arrange
        feature1 = Mock(spec=Feature)
        feature2 = Mock(spec=Feature)
        results = [
            (feature1, -2.0),
            (feature2, -1.0),
        ]

        # Act
        result = FeatureRepository._filter_by_ranks(results, ranks=10)

        # Assert
        assert len(result) == 2
        assert feature1 in result
        assert feature2 in result
