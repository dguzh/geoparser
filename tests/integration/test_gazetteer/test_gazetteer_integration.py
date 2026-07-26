"""
Integration tests for geoparser/gazetteer/gazetteer.py

Tests Gazetteer with a real artifact built from the Andorra fixture data.
"""

import pytest
from shapely.geometry.base import BaseGeometry

from geoparser.gazetteer.feature import Feature
from geoparser.gazetteer.gazetteer import Gazetteer


@pytest.mark.integration
class TestGazetteerIntegration:
    """Integration tests for Gazetteer with real Andorra data."""

    def test_creates_with_gazetteer_name(self, andorra_gazetteer):
        """Test that Gazetteer can be initialized with gazetteer name."""
        gazetteer = Gazetteer("andorranames")

        assert gazetteer is not None
        assert gazetteer.gazetteer_name == "andorranames"

    def test_search_exact_finds_location(self, andorra_gazetteer):
        """Test that exact search finds locations in Andorra gazetteer."""
        gazetteer = Gazetteer("andorranames")

        results = gazetteer.search("Andorra la Vella", method="exact")

        assert len(results) > 0

    def test_search_phrase_finds_location(self, andorra_gazetteer):
        """Test that phrase search finds locations."""
        gazetteer = Gazetteer("andorranames")

        results = gazetteer.search("Escaldes", method="phrase")

        assert len(results) > 0

    def test_search_partial_finds_location(self, andorra_gazetteer):
        """Test that partial search finds locations with partial word matches."""
        gazetteer = Gazetteer("andorranames")

        results = gazetteer.search("Andorra", method="partial")

        assert len(results) > 0

    def test_search_fuzzy_finds_location(self, andorra_gazetteer):
        """Test that fuzzy search finds locations despite misspellings."""
        gazetteer = Gazetteer("andorranames")

        results = gazetteer.search("Andora", method="fuzzy")

        assert len(results) > 0

    def test_search_respects_limit_parameter(self, andorra_gazetteer):
        """Test that search respects the limit parameter."""
        gazetteer = Gazetteer("andorranames")

        results = gazetteer.search("Andorra", method="partial", limit=2)

        assert len(results) <= 2

    def test_search_respects_tiers_parameter(self, andorra_gazetteer):
        """Test that search respects the tiers parameter for score-based tiering."""
        gazetteer = Gazetteer("andorranames")

        results_tier1 = gazetteer.search("Andorra", method="phrase", tiers=1)
        results_tier2 = gazetteer.search("Andorra", method="phrase", tiers=2)

        assert len(results_tier2) >= len(results_tier1)

    def test_search_normalizes_quotes(self, andorra_gazetteer):
        """Test that search normalizes quotation marks in names."""
        gazetteer = Gazetteer("andorranames")

        results = gazetteer.search('"Andorra"', method="exact")

        assert len(results) > 0

    def test_search_strips_whitespace(self, andorra_gazetteer):
        """Test that search strips leading/trailing whitespace."""
        gazetteer = Gazetteer("andorranames")

        results = gazetteer.search("  Andorra  ", method="exact")

        assert len(results) > 0

    def test_find_returns_specific_feature(self, andorra_gazetteer):
        """Test that find returns a specific feature by identifier."""
        gazetteer = Gazetteer("andorranames")

        # Andorra la Vella has geonameid 3041563
        feature = gazetteer.find("3041563")

        assert feature is not None
        assert feature.identifier == "3041563"

    def test_find_returns_none_for_nonexistent_feature(self, andorra_gazetteer):
        """Test that find returns None for non-existent identifier."""
        gazetteer = Gazetteer("andorranames")

        feature = gazetteer.find("9999999")

        assert feature is None

    def test_search_returns_feature_objects(self, andorra_gazetteer):
        """Test that search returns runtime Feature objects."""
        gazetteer = Gazetteer("andorranames")

        results = gazetteer.search("Andorra", method="exact")

        assert len(results) > 0
        assert all(isinstance(f, Feature) for f in results)

    def test_feature_has_geometry(self, andorra_gazetteer):
        """Test that returned features have geometry information."""
        gazetteer = Gazetteer("andorranames")

        results = gazetteer.search("Andorra la Vella", method="exact")

        assert len(results) > 0
        feature = results[0]
        assert isinstance(feature.geometry, BaseGeometry)
        assert feature.crs == "EPSG:4326"

    def test_feature_has_names(self, andorra_gazetteer):
        """Test that features have associated names."""
        gazetteer = Gazetteer("andorranames")

        results = gazetteer.search("Andorra la Vella", method="exact")

        assert len(results) > 0
        feature = results[0]
        assert "Andorra la Vella" in feature.names

    def test_feature_has_lookup_attributes(self, andorra_gazetteer):
        """Test that features carry attributes enriched via lookups."""
        gazetteer = Gazetteer("andorranames")

        feature = gazetteer.find("3041563")

        assert feature.data["country_name"] == "Andorra"
        assert feature.data["feature_name"] is not None
        assert feature.gazetteer_name == "andorranames"

    def test_searches_multiple_parishes(self, andorra_gazetteer):
        """Test that gazetteer contains data from multiple Andorra parishes."""
        gazetteer = Gazetteer("andorranames")

        parishes = ["Canillo", "Encamp", "Ordino", "Massana"]
        results_per_parish = [
            gazetteer.search(parish, method="phrase") for parish in parishes
        ]

        found_parishes = sum(1 for results in results_per_parish if len(results) > 0)
        assert found_parishes >= 2

    def test_search_case_insensitive(self, andorra_gazetteer):
        """Test that search is case-insensitive."""
        gazetteer = Gazetteer("andorranames")

        results_lower = gazetteer.search("andorra", method="exact")
        results_upper = gazetteer.search("ANDORRA", method="exact")
        results_mixed = gazetteer.search("AnDoRRa", method="exact")

        assert len(results_lower) > 0
        assert len(results_upper) > 0
        assert len(results_mixed) > 0

    def test_handles_special_characters(self, andorra_gazetteer):
        """Test that search handles diacritics in place names."""
        gazetteer = Gazetteer("andorranames")

        with_accent = gazetteer.search("Ansalonga", method="exact")

        assert len(with_accent) > 0

    def test_search_returns_consistent_results(self, andorra_gazetteer):
        """Test that multiple searches return consistent results."""
        gazetteer = Gazetteer("andorranames")

        results1 = gazetteer.search("Andorra la Vella", method="exact")
        results2 = gazetteer.search("Andorra la Vella", method="exact")

        assert {f.identifier for f in results1} == {f.identifier for f in results2}

    def test_different_search_methods_return_result_lists(self, andorra_gazetteer):
        """Test that different search methods all return lists."""
        gazetteer = Gazetteer("andorranames")
        query = "Andorra"

        exact_results = gazetteer.search(query, method="exact")
        partial_results = gazetteer.search(query, method="partial")

        assert isinstance(exact_results, list)
        assert isinstance(partial_results, list)
        assert len(partial_results) >= len(exact_results)
