"""
Unit tests for geoparser/db/functions/levenshtein.py
"""

import pytest

from geoparser.db.functions.levenshtein import levenshtein


@pytest.mark.unit
class TestLevenshtein:
    """Test the levenshtein() function."""

    def test_returns_zero_for_identical_strings(self):
        """Test that identical strings have a distance of zero."""
        assert levenshtein("Paris", "Paris") == 0

    def test_is_case_insensitive(self):
        """Test that comparison is case-insensitive."""
        assert levenshtein("paris", "PARIS") == 0

    def test_counts_single_edit(self):
        """Test that a single-character difference yields a distance of one."""
        assert levenshtein("Andorra", "Andora") == 1

    def test_returns_higher_distance_for_dissimilar_strings(self):
        """Test that dissimilar strings have a larger distance than similar ones."""
        close = levenshtein("Andorra", "Andora")
        far = levenshtein("Andorra", "Berlin")
        assert close < far

    def test_treats_none_query_as_empty_string(self):
        """Test that a None query is treated as an empty string."""
        assert levenshtein(None, "Paris") == 5

    def test_treats_none_candidate_as_empty_string(self):
        """Test that a None candidate is treated as an empty string."""
        assert levenshtein("Paris", None) == 5
