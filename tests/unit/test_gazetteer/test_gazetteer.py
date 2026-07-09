"""
Unit tests for geoparser/gazetteer/gazetteer.py

Tests the Gazetteer query interface against small hand-crafted artifacts.
"""

import pytest
from shapely.geometry import Point

from geoparser.gazetteer.feature import Feature
from geoparser.gazetteer.gazetteer import Gazetteer


@pytest.mark.unit
class TestGazetteerInitialization:
    """Test Gazetteer initialization."""

    def test_creates_with_gazetteer_name(self, make_artifact):
        """Test that Gazetteer can be created for an installed artifact."""
        make_artifact(name="testgaz")

        gazetteer = Gazetteer("testgaz")

        assert gazetteer.gazetteer_name == "testgaz"

    def test_raises_when_gazetteer_not_installed(self, make_artifact):
        """Test that constructing an uninstalled gazetteer raises ValueError."""
        with pytest.raises(ValueError, match="not installed"):
            Gazetteer("not-installed-gazetteer")

    def test_raises_on_incompatible_schema_version(self, make_artifact):
        """An artifact with an old schema version asks for a reinstall."""
        make_artifact(name="oldgaz", schema_version="0")

        with pytest.raises(RuntimeError, match="reinstall"):
            Gazetteer("oldgaz")

    def test_exposes_artifact_crs(self, make_artifact):
        """The gazetteer exposes the artifact's CRS."""
        make_artifact(name="testgaz", crs="EPSG:4326")

        assert Gazetteer("testgaz").crs == "EPSG:4326"


@pytest.mark.unit
class TestGazetteerSearch:
    """Test Gazetteer search method."""

    def test_search_exact_matches_full_name_only(self, make_artifact):
        """Exact search matches complete names, not substrings."""
        make_artifact()

        results = Gazetteer("testgaz").search("Paris", method="exact")

        assert {feature.identifier for feature in results} == {"1"}

    def test_search_exact_is_case_insensitive(self, make_artifact):
        """Exact search is case-insensitive."""
        make_artifact()

        results = Gazetteer("testgaz").search("paris", method="exact")

        assert {feature.identifier for feature in results} == {"1"}

    def test_search_phrase_matches_names_containing_query(self, make_artifact):
        """Phrase search finds names containing the query as a phrase."""
        make_artifact()

        results = Gazetteer("testgaz").search("Paris", method="phrase", tiers=2)

        assert {feature.identifier for feature in results} == {"1", "3"}

    def test_search_partial_matches_some_tokens(self, make_artifact):
        """Partial search matches a subset of the query tokens."""
        make_artifact()

        results = Gazetteer("testgaz").search("Paris Berlin", method="partial", tiers=3)

        assert {feature.identifier for feature in results} == {"1", "2", "3"}

    def test_search_fuzzy_matches_misspelled_name(self, make_artifact):
        """Fuzzy search finds names that sound like the query."""
        make_artifact()

        results = Gazetteer("testgaz").search("Barlin", method="fuzzy")

        assert {feature.identifier for feature in results} == {"2"}

    def test_search_normalizes_quotes_and_whitespace(self, make_artifact):
        """Quotes are removed and whitespace stripped before searching."""
        make_artifact()

        results = Gazetteer("testgaz").search('  "Paris"  ', method="exact")

        assert {feature.identifier for feature in results} == {"1"}

    def test_search_respects_limit(self, make_artifact):
        """The limit caps the number of results."""
        make_artifact(
            features=[
                {"identifier": str(index), "names": ["Springfield"]}
                for index in range(1, 6)
            ]
        )

        results = Gazetteer("testgaz").search("Springfield", method="exact", limit=3)

        assert len(results) == 3

    def test_search_tiers_expand_results(self, make_artifact):
        """More tiers include worse-ranked matches."""
        make_artifact()
        gazetteer = Gazetteer("testgaz")

        one_tier = gazetteer.search("Paris", method="phrase", tiers=1)
        two_tiers = gazetteer.search("Paris", method="phrase", tiers=2)

        assert {feature.identifier for feature in one_tier} == {"1"}
        assert {feature.identifier for feature in two_tiers} == {"1", "3"}

    def test_search_raises_error_for_unknown_method(self, make_artifact):
        """Unknown search methods raise ValueError."""
        make_artifact()

        with pytest.raises(ValueError, match="Unknown search method: invalid"):
            Gazetteer("testgaz").search("Paris", method="invalid")

    def test_search_returns_feature_objects(self, make_artifact):
        """Search results are Feature objects with attribute access."""
        make_artifact()

        results = Gazetteer("testgaz").search("Berlin", method="exact")

        assert len(results) == 1
        feature = results[0]
        assert isinstance(feature, Feature)
        assert feature.identifier == "2"
        assert feature.type == "city"
        assert feature.data["population"] == 3600000
        assert feature.gazetteer_name == "testgaz"

    def test_search_returns_empty_list_when_nothing_matches(self, make_artifact):
        """A query matching nothing returns an empty list."""
        make_artifact()

        assert Gazetteer("testgaz").search("Atlantis", method="exact") == []

    def test_empty_query_returns_empty_list(self, make_artifact):
        """Empty or whitespace-only queries return no results."""
        make_artifact()
        gazetteer = Gazetteer("testgaz")

        assert gazetteer.search("", method="exact") == []
        assert gazetteer.search('  ""  ', method="phrase") == []


@pytest.mark.unit
class TestGazetteerFind:
    """Test Gazetteer find method."""

    def test_find_returns_feature_by_identifier(self, make_artifact):
        """Find returns the feature with the given identifier."""
        make_artifact()

        feature = Gazetteer("testgaz").find("1")

        assert feature is not None
        assert feature.identifier == "1"
        assert feature.data["name"] == "Paris"

    def test_find_returns_none_when_not_found(self, make_artifact):
        """Find returns None for unknown identifiers."""
        make_artifact()

        assert Gazetteer("testgaz").find("999999") is None


@pytest.mark.unit
class TestFeature:
    """Test the runtime Feature class."""

    def test_names_are_loaded_from_artifact(self, make_artifact):
        """Feature.names returns all searchable names."""
        make_artifact()

        feature = Gazetteer("testgaz").find("1")

        assert feature.names == ["Paris", "Lutetia"]

    def test_geometry_is_none_when_absent(self, make_artifact):
        """Features without geometry return None."""
        make_artifact()

        feature = Gazetteer("testgaz").find("1")

        assert feature.geometry is None

    def test_geometry_is_parsed_from_wkb(self, make_artifact):
        """WKB geometry is parsed into a Shapely object."""
        point = Point(1.5, 42.5)
        make_artifact(
            features=[
                {"identifier": "1", "names": ["Somewhere"], "geometry": point.wkb}
            ]
        )

        feature = Gazetteer("testgaz").find("1")

        assert feature.geometry.equals(point)
        assert feature.crs == "EPSG:4326"

    def test_equality_is_by_gazetteer_and_identifier(self, make_artifact):
        """Two lookups of the same feature compare equal."""
        make_artifact()
        gazetteer = Gazetteer("testgaz")

        assert gazetteer.find("1") == gazetteer.find("1")
        assert gazetteer.find("1") != gazetteer.find("2")

    def test_string_representation(self, make_artifact):
        """Features render as Feature(gazetteer:identifier)."""
        make_artifact()

        assert str(Gazetteer("testgaz").find("1")) == "Feature(testgaz:1)"
