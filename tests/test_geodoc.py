import typing as t

import pytest

from geoparser.geodoc import GeoDoc
from geoparser.geodoc.geodoc import Locations
from geoparser.geospan import GeoSpan


@pytest.fixture(scope="session")
def locations(geonames_real_data, radio_andorra_id) -> Locations:
    locations = Locations(geonames_real_data.query_location_info([radio_andorra_id]))
    return locations


def test_locations_repr(locations: Locations):
    assert (
        locations.__repr__() == "[{'geonameid': '3039328', "
        "'name': 'Radio Andorra', "
        "'feature_type': 'radio station', "
        "'latitude': 42.5282, "
        "'longitude': 1.57089, "
        "'elevation': None, "
        "'population': 0, "
        "'admin2_geonameid': None, "
        "'admin2_name': None, "
        "'admin1_geonameid': '3040684', "
        "'admin1_name': 'Encamp', "
        "'country_geonameid': '3041565', "
        "'country_name': 'Andorra'}]"
    )


@pytest.mark.parametrize(
    "key,expected",
    [
        ("name", ["Radio Andorra"]),
        (("name", "admin1_name"), [("Radio Andorra", "Encamp")]),
        ("non_existing", [None]),
    ],
)
def test_locations_access(
    locations: Locations, key: t.Optional[str], expected: t.Union[str, int, float, None]
):
    assert locations[key] == expected


def test_geodoc_locations(geodocs: list[GeoDoc]):
    for elem in geodocs:
        locations = elem.locations
        assert type(locations) is Locations
        assert len(locations["name"]) == 1


def test_geodoc_toponyms(geodocs: list[GeoDoc]):
    for elem in geodocs:
        toponyms = elem.toponyms
        assert type(toponyms) is tuple
        assert type(toponyms[0]) is GeoSpan
        assert len(toponyms) == 1
