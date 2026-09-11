"""
Tests for how Gazetteer.search dispatches to the artifact.

The search method, the result limit and the tier count all reach a different
artifact query depending on the method asked for. Dropping one of them, or
changing a default, still returns plausible results while quietly searching
for something other than what was asked.
"""

from unittest.mock import Mock

import pytest

from geoparser.gazetteer.gazetteer import Gazetteer


@pytest.fixture
def gazetteer():
    """A Gazetteer whose artifact records the queries it receives."""
    instance = Gazetteer.__new__(Gazetteer)
    instance._artifact = Mock()
    for query in ("search_exact", "search_phrase", "search_partial", "search_fuzzy"):
        getattr(instance._artifact, query).return_value = []
    return instance


@pytest.mark.unit
class TestSearchDispatch:
    """Which artifact query each method reaches, and with what."""

    def test_defaults_to_an_exact_search_of_one_tier(self, gazetteer):
        """
        With no method given the search is exact, over a single tier.

        The defaults are part of the contract: widening them silently changes
        what every caller that omits them gets back.
        """
        # Act
        gazetteer.search("Paris")

        # Assert
        gazetteer._artifact.search_exact.assert_called_once_with("Paris", 10000)
        gazetteer._artifact.search_phrase.assert_not_called()

    @pytest.mark.parametrize(
        ("method", "query"),
        [
            ("phrase", "search_phrase"),
            ("partial", "search_partial"),
            ("fuzzy", "search_fuzzy"),
        ],
    )
    def test_ranked_methods_receive_the_name_limit_and_tiers(
        self, gazetteer, method, query
    ):
        """Every ranked query is given all three arguments, in order."""
        # Act
        gazetteer.search("Paris", method=method, limit=25, tiers=3)

        # Assert
        getattr(gazetteer._artifact, query).assert_called_once_with("Paris", 25, 3)

    def test_exact_search_ignores_tiers(self, gazetteer):
        """An exact match has no ranking, so it takes only name and limit."""
        # Act
        gazetteer.search("Paris", method="exact", limit=25, tiers=3)

        # Assert
        gazetteer._artifact.search_exact.assert_called_once_with("Paris", 25)

    def test_strips_quotes_and_surrounding_whitespace(self, gazetteer):
        """Quotes would be taken as syntax by the underlying full-text query."""
        # Act
        gazetteer.search('  "Paris"  ')

        # Assert
        gazetteer._artifact.search_exact.assert_called_once_with("Paris", 10000)

    def test_returns_nothing_for_a_name_that_normalises_to_empty(self, gazetteer):
        """A name of only quotes and spaces is not searched for at all."""
        # Act
        results = gazetteer.search('  ""  ')

        # Assert
        assert results == []
        gazetteer._artifact.search_exact.assert_not_called()

    def test_rejects_an_unknown_method(self, gazetteer):
        """A misspelled method is reported rather than silently ignored."""
        # Act & Assert
        with pytest.raises(ValueError, match="soundslike"):
            gazetteer.search("Paris", method="soundslike")

    def test_returns_what_the_artifact_returned(self, gazetteer):
        """Results are passed straight through."""
        # Arrange
        feature = Mock()
        gazetteer._artifact.search_exact.return_value = [feature]

        # Act & Assert
        assert gazetteer.search("Paris") == [feature]
