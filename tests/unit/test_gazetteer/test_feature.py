"""
Unit tests for geoparser/gazetteer/feature.py

Tests the runtime Feature class against small hand-crafted artifacts.
"""

import pytest
from shapely.geometry import Point

from geoparser.gazetteer.gazetteer import Gazetteer


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

    def test_equality_with_non_feature_is_not_equal(self, make_artifact):
        """Comparing a feature to a non-feature object is never equal."""
        make_artifact()

        assert Gazetteer("testgaz").find("1") != "not-a-feature"

    def test_hash_is_by_gazetteer_and_identifier(self, make_artifact):
        """Features with the same gazetteer and identifier hash equally."""
        make_artifact()
        gazetteer = Gazetteer("testgaz")

        assert hash(gazetteer.find("1")) == hash(gazetteer.find("1"))
        assert hash(gazetteer.find("1")) != hash(gazetteer.find("2"))

    def test_string_representation(self, make_artifact):
        """Features render as Feature(gazetteer:identifier)."""
        make_artifact()

        assert str(Gazetteer("testgaz").find("1")) == "Feature(testgaz:1)"

    def test_repr_matches_string_representation(self, make_artifact):
        """repr() renders the same as str()."""
        make_artifact()

        feature = Gazetteer("testgaz").find("1")

        assert repr(feature) == str(feature) == "Feature(testgaz:1)"
