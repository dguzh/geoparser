"""
Tests for how the Levenshtein SQL function handles NULL.

SQLite passes NULL through as ``None``, and the fuzzy search ranks on this
function's result. A NULL that were treated as some placeholder string rather
than as the empty string would score every row against that placeholder,
quietly reordering the candidates instead of failing.
"""

import pytest

from geoparser.db.functions.levenshtein import levenshtein


@pytest.mark.unit
class TestNullOperands:
    """A missing operand counts as the empty string."""

    def test_a_null_query_costs_the_length_of_the_candidate(self):
        """Turning nothing into "Paris" costs one insertion per character."""
        # Act & Assert
        assert levenshtein(None, "Paris") == len("Paris")

    def test_a_null_candidate_costs_the_length_of_the_query(self):
        """The distance is symmetric, so the same holds the other way round."""
        # Act & Assert
        assert levenshtein("Paris", None) == len("Paris")

    def test_two_nulls_are_an_exact_match(self):
        """Nothing is zero edits away from nothing."""
        # Act & Assert
        assert levenshtein(None, None) == 0
