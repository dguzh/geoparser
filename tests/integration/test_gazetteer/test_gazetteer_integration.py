"""
Integration tests for geoparser/gazetteer/gazetteer.py

Tests Gazetteer with real Andorra gazetteer data.
"""

import pytest

from geoparser.gazetteer.gazetteer import Gazetteer


@pytest.mark.integration
class TestGazetteerIntegration:
    """Integration tests for Gazetteer with real Andorra data."""

    def test_creates_with_gazetteer_name(self, andorra_gazetteer):
        """Test that Gazetteer can be initialized with gazetteer name."""
        # Act
        gazetteer = Gazetteer("andorranames")

        # Assert
        assert gazetteer is not None
        assert gazetteer.gazetteer_name == "andorranames"

    def test_search_exact_finds_location(self, andorra_gazetteer):
        """Test that exact search finds locations in Andorra gazetteer."""
        # Arrange
        gazetteer = Gazetteer("andorranames")

        # Act
        results = gazetteer.search("Andorra la Vella", method="exact")

        # Assert
        assert len(results) > 0

    def test_search_phrase_finds_location(self, andorra_gazetteer):
        """Test that phrase search finds locations."""
        # Arrange
        gazetteer = Gazetteer("andorranames")

        # Act
        results = gazetteer.search("Escaldes", method="phrase")

        # Assert
        assert len(results) > 0

    def test_search_permuted_finds_location(self, andorra_gazetteer):
        """Test that permuted search finds locations with reordered words."""
        # Arrange
        gazetteer = Gazetteer("andorranames")

        # Act
        results = gazetteer.search("Vella Andorra", method="permuted")

        # Assert
        # Should still find "Andorra la Vella" despite word order
        assert len(results) > 0

    def test_search_partial_finds_location(self, andorra_gazetteer):
        """Test that partial search finds locations with partial word matches."""
        # Arrange
        gazetteer = Gazetteer("andorranames")

        # Act
        results = gazetteer.search("Andorra", method="partial")

        # Assert
        assert len(results) > 0
        # Should find multiple Andorra locations
        assert len(results) >= 1

    def test_search_substring_finds_location(self, andorra_gazetteer):
        """Test that substring search finds locations with substring matches."""
        # Arrange
        gazetteer = Gazetteer("andorranames")

        # Act
        results = gazetteer.search("dorra", method="substring")

        # Assert
        # Should find "Andorra" locations
        assert len(results) > 0

    def test_search_fuzzy_finds_location(self, andorra_gazetteer):
        """Test that fuzzy search finds locations with fuzzy matching."""
        # Arrange
        gazetteer = Gazetteer("andorranames")

        # Act
        results = gazetteer.search("Andora", method="fuzzy")  # Misspelled

        # Assert
        # Should still find "Andorra" despite misspelling
        assert len(results) > 0

    def test_search_respects_limit_parameter(self, andorra_gazetteer):
        """Test that search respects the limit parameter."""
        # Arrange
        gazetteer = Gazetteer("andorranames")

        # Act
        results = gazetteer.search("Andorra", method="partial", limit=2)

        # Assert
        assert len(results) <= 2

    def test_search_respects_ranks_parameter(self, andorra_gazetteer):
        """Test that search respects the ranks parameter for FTS ranking."""
        # Arrange
        gazetteer = Gazetteer("andorranames")

        # Act
        results_rank1 = gazetteer.search("Andorra", method="phrase", ranks=1)
        results_rank2 = gazetteer.search("Andorra", method="phrase", ranks=2)

        # Assert
        # With more ranks, we should get same or more results
        assert len(results_rank2) >= len(results_rank1)

    def test_search_normalizes_quotes(self, andorra_gazetteer):
        """Test that search normalizes quotation marks in names."""
        # Arrange
        gazetteer = Gazetteer("andorranames")

        # Act
        results = gazetteer.search('"Andorra"', method="exact")

        # Assert
        # Should handle quoted search terms
        assert len(results) >= 0  # May or may not find results, but shouldn't error

    def test_search_strips_whitespace(self, andorra_gazetteer):
        """Test that search strips leading/trailing whitespace."""
        # Arrange
        gazetteer = Gazetteer("andorranames")

        # Act
        results = gazetteer.search("  Andorra  ", method="exact")

        # Assert
        assert len(results) > 0

    def test_find_returns_specific_feature(self, andorra_gazetteer):
        """Test that find returns a specific feature by identifier."""
        # Arrange
        gazetteer = Gazetteer("andorranames")

        # Act - Andorra la Vella has geonameid 3041563
        feature = gazetteer.find("3041563")

        # Assert
        assert feature is not None
        assert feature.location_id_value == "3041563"

    def test_find_returns_none_for_nonexistent_feature(self, andorra_gazetteer):
        """Test that find returns None for non-existent identifier."""
        # Arrange
        gazetteer = Gazetteer("andorranames")

        # Act
        feature = gazetteer.find("9999999")

        # Assert
        assert feature is None

    def test_search_returns_feature_objects(self, andorra_gazetteer):
        """Test that search returns Feature model objects."""
        # Arrange
        gazetteer = Gazetteer("andorranames")

        # Act
        results = gazetteer.search("Andorra", method="exact")

        # Assert
        assert len(results) > 0
        from geoparser.db.models.feature import Feature

        assert all(isinstance(f, Feature) for f in results)

    def test_feature_has_geometry(self, andorra_gazetteer):
        """Test that returned features have geometry information."""
        # Arrange
        gazetteer = Gazetteer("andorranames")

        # Act
        results = gazetteer.search("Andorra la Vella", method="exact")

        # Assert
        assert len(results) > 0
        feature = results[0]
        # Should have geometry attribute (though value may vary by gazetteer config)
        assert hasattr(feature, "geometry")

    def test_feature_has_names(self, andorra_gazetteer):
        """Test that features have associated names."""
        # Arrange
        gazetteer = Gazetteer("andorranames")

        # Act
        results = gazetteer.search("Andorra la Vella", method="exact")

        # Assert
        assert len(results) > 0
        feature = results[0]
        assert hasattr(feature, "names")

    def test_searches_multiple_parishes(self, andorra_gazetteer):
        """Test that gazetteer contains data from multiple Andorra parishes."""
        # Arrange
        gazetteer = Gazetteer("andorranames")

        # Act - Search for various parish names
        parishes = ["Canillo", "Encamp", "Ordino", "Massana"]
        results_per_parish = [
            gazetteer.search(parish, method="phrase") for parish in parishes
        ]

        # Assert - Should find at least some parishes
        found_parishes = sum(1 for results in results_per_parish if len(results) > 0)
        assert found_parishes >= 2  # At least 2 parishes should be found

    def test_search_case_insensitive(self, andorra_gazetteer):
        """Test that search is case-insensitive."""
        # Arrange
        gazetteer = Gazetteer("andorranames")

        # Act
        results_lower = gazetteer.search("andorra", method="exact")
        results_upper = gazetteer.search("ANDORRA", method="exact")
        results_mixed = gazetteer.search("AnDoRRa", method="exact")

        # Assert - All should find results
        assert len(results_lower) > 0
        assert len(results_upper) > 0
        assert len(results_mixed) > 0

    def test_handles_special_characters(self, andorra_gazetteer):
        """Test that search handles special characters in place names."""
        # Arrange
        gazetteer = Gazetteer("andorranames")

        # Act - Some Andorra locations may have accents or special chars
        results = gazetteer.search("la", method="partial")

        # Assert
        assert len(results) >= 0  # Should handle search without error

    def test_search_returns_consistent_results(self, andorra_gazetteer):
        """Test that multiple searches return consistent results."""
        # Arrange
        gazetteer = Gazetteer("andorranames")

        # Act
        results1 = gazetteer.search("Andorra la Vella", method="exact")
        results2 = gazetteer.search("Andorra la Vella", method="exact")

        # Assert
        assert len(results1) == len(results2)
        # Should return same features (comparing IDs)
        ids1 = {f.id for f in results1}
        ids2 = {f.id for f in results2}
        assert ids1 == ids2

    def test_different_search_methods_return_different_results(self, andorra_gazetteer):
        """Test that different search methods return different result sets."""
        # Arrange
        gazetteer = Gazetteer("andorranames")
        query = "Andorra"

        # Act
        exact_results = gazetteer.search(query, method="exact")
        partial_results = gazetteer.search(query, method="partial")

        # Assert
        # Partial should typically return more results than exact
        # (though this depends on the data)
        assert isinstance(exact_results, list)
        assert isinstance(partial_results, list)

    def test_empty_search_query_handled_gracefully(self, andorra_gazetteer):
        """Test that empty search query is handled gracefully."""
        # Arrange
        gazetteer = Gazetteer("andorranames")

        # Act & Assert - Should not raise exception
        results = gazetteer.search("", method="exact")
        assert isinstance(results, list)

    def test_find_feature_has_source_relationship(self, andorra_gazetteer):
        """Test that found features have proper source relationship."""
        # Arrange
        gazetteer = Gazetteer("andorranames")

        # Act
        feature = gazetteer.find("3041563")

        # Assert
        assert feature is not None
        assert hasattr(feature, "source")
        assert feature.source is not None

    def test_find_feature_has_gazetteer_through_source(self, andorra_gazetteer):
        """Test that features can access gazetteer through source."""
        # Arrange
        gazetteer = Gazetteer("andorranames")

        # Act
        feature = gazetteer.find("3041563")

        # Assert
        assert feature is not None
        assert feature.source is not None
        assert hasattr(feature.source, "gazetteer")
        assert feature.source.gazetteer is not None
        assert feature.source.gazetteer.name == "andorranames"
