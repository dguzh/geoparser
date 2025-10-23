"""
Unit tests for geoparser/gazetteer/gazetteer.py

Tests the Gazetteer class with mocked FeatureRepository.
"""

from unittest.mock import Mock, patch

import pytest

from geoparser.gazetteer.gazetteer import Gazetteer


@pytest.mark.unit
class TestGazetteerInitialization:
    """Test Gazetteer initialization."""

    def test_creates_with_gazetteer_name(self):
        """Test that Gazetteer can be created with a gazetteer name."""
        # Arrange & Act
        gazetteer = Gazetteer("geonames")

        # Assert
        assert gazetteer.gazetteer_name == "geonames"


@pytest.mark.unit
class TestGazetteerSearch:
    """Test Gazetteer search method."""

    @patch("geoparser.gazetteer.gazetteer.Session")
    @patch("geoparser.gazetteer.gazetteer.FeatureRepository")
    def test_search_with_exact_method(self, mock_feature_repo, mock_session):
        """Test that search calls exact method correctly."""
        # Arrange
        mock_db = Mock()
        mock_session.return_value.__enter__.return_value = mock_db
        mock_feature_repo.get_by_gazetteer_and_name_exact.return_value = []

        gazetteer = Gazetteer("geonames")

        # Act
        gazetteer.search("Paris", method="exact")

        # Assert
        mock_feature_repo.get_by_gazetteer_and_name_exact.assert_called_once_with(
            mock_db, "geonames", "Paris", 1000
        )

    @patch("geoparser.gazetteer.gazetteer.Session")
    @patch("geoparser.gazetteer.gazetteer.FeatureRepository")
    def test_search_with_phrase_method(self, mock_feature_repo, mock_session):
        """Test that search calls phrase method correctly."""
        # Arrange
        mock_db = Mock()
        mock_session.return_value.__enter__.return_value = mock_db
        mock_feature_repo.get_by_gazetteer_and_name_phrase.return_value = []

        gazetteer = Gazetteer("geonames")

        # Act
        gazetteer.search("Paris", method="phrase", ranks=2)

        # Assert
        mock_feature_repo.get_by_gazetteer_and_name_phrase.assert_called_once_with(
            mock_db, "geonames", "Paris", 1000, 2
        )

    @patch("geoparser.gazetteer.gazetteer.Session")
    @patch("geoparser.gazetteer.gazetteer.FeatureRepository")
    def test_search_with_permuted_method(self, mock_feature_repo, mock_session):
        """Test that search calls permuted method correctly."""
        # Arrange
        mock_db = Mock()
        mock_session.return_value.__enter__.return_value = mock_db
        mock_feature_repo.get_by_gazetteer_and_name_permuted.return_value = []

        gazetteer = Gazetteer("geonames")

        # Act
        gazetteer.search("New York", method="permuted")

        # Assert
        mock_feature_repo.get_by_gazetteer_and_name_permuted.assert_called_once_with(
            mock_db, "geonames", "New York", 1000, 1
        )

    @patch("geoparser.gazetteer.gazetteer.Session")
    @patch("geoparser.gazetteer.gazetteer.FeatureRepository")
    def test_search_with_partial_method(self, mock_feature_repo, mock_session):
        """Test that search calls partial method correctly."""
        # Arrange
        mock_db = Mock()
        mock_session.return_value.__enter__.return_value = mock_db
        mock_feature_repo.get_by_gazetteer_and_name_partial.return_value = []

        gazetteer = Gazetteer("geonames")

        # Act
        gazetteer.search("Paris", method="partial")

        # Assert
        mock_feature_repo.get_by_gazetteer_and_name_partial.assert_called_once_with(
            mock_db, "geonames", "Paris", 1000, 1
        )

    @patch("geoparser.gazetteer.gazetteer.Session")
    @patch("geoparser.gazetteer.gazetteer.FeatureRepository")
    def test_search_with_substring_method(self, mock_feature_repo, mock_session):
        """Test that search calls substring method correctly."""
        # Arrange
        mock_db = Mock()
        mock_session.return_value.__enter__.return_value = mock_db
        mock_feature_repo.get_by_gazetteer_and_name_substring.return_value = []

        gazetteer = Gazetteer("geonames")

        # Act
        gazetteer.search("Paris", method="substring")

        # Assert
        mock_feature_repo.get_by_gazetteer_and_name_substring.assert_called_once_with(
            mock_db, "geonames", "Paris", 1000, 1
        )

    @patch("geoparser.gazetteer.gazetteer.Session")
    @patch("geoparser.gazetteer.gazetteer.FeatureRepository")
    def test_search_with_fuzzy_method(self, mock_feature_repo, mock_session):
        """Test that search calls fuzzy method correctly."""
        # Arrange
        mock_db = Mock()
        mock_session.return_value.__enter__.return_value = mock_db
        mock_feature_repo.get_by_gazetteer_and_name_fuzzy.return_value = []

        gazetteer = Gazetteer("geonames")

        # Act
        gazetteer.search("Paris", method="fuzzy")

        # Assert
        mock_feature_repo.get_by_gazetteer_and_name_fuzzy.assert_called_once_with(
            mock_db, "geonames", "Paris", 1000, 1
        )

    @patch("geoparser.gazetteer.gazetteer.Session")
    @patch("geoparser.gazetteer.gazetteer.FeatureRepository")
    def test_search_normalizes_quotes_from_name(self, mock_feature_repo, mock_session):
        """Test that search removes quotes from name before searching."""
        # Arrange
        mock_db = Mock()
        mock_session.return_value.__enter__.return_value = mock_db
        mock_feature_repo.get_by_gazetteer_and_name_exact.return_value = []

        gazetteer = Gazetteer("geonames")

        # Act
        gazetteer.search('"Paris"', method="exact")

        # Assert
        # Should call with quotes removed
        mock_feature_repo.get_by_gazetteer_and_name_exact.assert_called_once_with(
            mock_db, "geonames", "Paris", 1000
        )

    @patch("geoparser.gazetteer.gazetteer.Session")
    @patch("geoparser.gazetteer.gazetteer.FeatureRepository")
    def test_search_strips_whitespace_from_name(self, mock_feature_repo, mock_session):
        """Test that search strips whitespace from name."""
        # Arrange
        mock_db = Mock()
        mock_session.return_value.__enter__.return_value = mock_db
        mock_feature_repo.get_by_gazetteer_and_name_exact.return_value = []

        gazetteer = Gazetteer("geonames")

        # Act
        gazetteer.search("  Paris  ", method="exact")

        # Assert
        # Should call with whitespace stripped
        mock_feature_repo.get_by_gazetteer_and_name_exact.assert_called_once_with(
            mock_db, "geonames", "Paris", 1000
        )

    @patch("geoparser.gazetteer.gazetteer.Session")
    @patch("geoparser.gazetteer.gazetteer.FeatureRepository")
    def test_search_respects_custom_limit(self, mock_feature_repo, mock_session):
        """Test that search respects custom limit parameter."""
        # Arrange
        mock_db = Mock()
        mock_session.return_value.__enter__.return_value = mock_db
        mock_feature_repo.get_by_gazetteer_and_name_exact.return_value = []

        gazetteer = Gazetteer("geonames")

        # Act
        gazetteer.search("Paris", method="exact", limit=50)

        # Assert
        mock_feature_repo.get_by_gazetteer_and_name_exact.assert_called_once_with(
            mock_db, "geonames", "Paris", 50
        )

    @patch("geoparser.gazetteer.gazetteer.Session")
    @patch("geoparser.gazetteer.gazetteer.FeatureRepository")
    def test_search_respects_custom_ranks(self, mock_feature_repo, mock_session):
        """Test that search respects custom ranks parameter for ranking methods."""
        # Arrange
        mock_db = Mock()
        mock_session.return_value.__enter__.return_value = mock_db
        mock_feature_repo.get_by_gazetteer_and_name_phrase.return_value = []

        gazetteer = Gazetteer("geonames")

        # Act
        gazetteer.search("Paris", method="phrase", ranks=3)

        # Assert
        mock_feature_repo.get_by_gazetteer_and_name_phrase.assert_called_once_with(
            mock_db, "geonames", "Paris", 1000, 3
        )

    def test_search_raises_error_for_unknown_method(self):
        """Test that search raises ValueError for unknown method."""
        # Arrange
        gazetteer = Gazetteer("geonames")

        # Act & Assert
        with pytest.raises(ValueError, match="Unknown search method: invalid"):
            gazetteer.search("Paris", method="invalid")

    @patch("geoparser.gazetteer.gazetteer.Session")
    @patch("geoparser.gazetteer.gazetteer.FeatureRepository")
    def test_search_returns_features(self, mock_feature_repo, mock_session):
        """Test that search returns the features from repository."""
        # Arrange
        mock_db = Mock()
        mock_session.return_value.__enter__.return_value = mock_db

        mock_feature1 = Mock()
        mock_feature2 = Mock()
        mock_feature_repo.get_by_gazetteer_and_name_exact.return_value = [
            mock_feature1,
            mock_feature2,
        ]

        gazetteer = Gazetteer("geonames")

        # Act
        results = gazetteer.search("Paris", method="exact")

        # Assert
        assert len(results) == 2
        assert results[0] == mock_feature1
        assert results[1] == mock_feature2


@pytest.mark.unit
class TestGazetteerFind:
    """Test Gazetteer find method."""

    @patch("geoparser.gazetteer.gazetteer.Session")
    @patch("geoparser.gazetteer.gazetteer.FeatureRepository")
    def test_find_calls_repository_method(self, mock_feature_repo, mock_session):
        """Test that find calls get_by_gazetteer_and_identifier."""
        # Arrange
        mock_db = Mock()
        mock_session.return_value.__enter__.return_value = mock_db
        mock_feature_repo.get_by_gazetteer_and_identifier.return_value = None

        gazetteer = Gazetteer("geonames")

        # Act
        gazetteer.find("123456")

        # Assert
        mock_feature_repo.get_by_gazetteer_and_identifier.assert_called_once_with(
            mock_db, "geonames", "123456"
        )

    @patch("geoparser.gazetteer.gazetteer.Session")
    @patch("geoparser.gazetteer.gazetteer.FeatureRepository")
    def test_find_returns_feature_when_found(self, mock_feature_repo, mock_session):
        """Test that find returns feature when found."""
        # Arrange
        mock_db = Mock()
        mock_session.return_value.__enter__.return_value = mock_db

        mock_feature = Mock()
        mock_feature_repo.get_by_gazetteer_and_identifier.return_value = mock_feature

        gazetteer = Gazetteer("geonames")

        # Act
        result = gazetteer.find("123456")

        # Assert
        assert result == mock_feature

    @patch("geoparser.gazetteer.gazetteer.Session")
    @patch("geoparser.gazetteer.gazetteer.FeatureRepository")
    def test_find_returns_none_when_not_found(self, mock_feature_repo, mock_session):
        """Test that find returns None when feature not found."""
        # Arrange
        mock_db = Mock()
        mock_session.return_value.__enter__.return_value = mock_db
        mock_feature_repo.get_by_gazetteer_and_identifier.return_value = None

        gazetteer = Gazetteer("geonames")

        # Act
        result = gazetteer.find("999999")

        # Assert
        assert result is None
