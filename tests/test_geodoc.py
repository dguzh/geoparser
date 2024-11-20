import pytest

from geoparser.geodoc import GeoDoc
from geoparser.geospan import GeoSpan


def test_geodoc_locations(geodocs: list[GeoDoc]):
    for elem in geodocs:
        locations = elem.locations
        assert isinstance(locations, list)
        assert all(isinstance(loc, (dict, type(None))) for loc in locations)
        assert len(locations) == 1


def test_geodoc_toponyms(geodocs: list[GeoDoc]):
    for elem in geodocs:
        toponyms = elem.toponyms
        assert isinstance(toponyms, tuple)
        assert all(isinstance(toponym, GeoSpan) for toponym in toponyms)
        assert len(toponyms) == 1
