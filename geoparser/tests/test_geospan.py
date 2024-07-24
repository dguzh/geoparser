import pytest

from geoparser.geodoc import GeoDoc
from geoparser.geospan import GeoSpan


@pytest.fixture(scope="session")
def first_geodoc(geodocs: list[GeoDoc]) -> GeoDoc:
    return geodocs[0]


@pytest.fixture(scope="session")
def second_geodoc(geodocs: list[GeoDoc]) -> GeoDoc:
    return geodocs[1]


@pytest.mark.parametrize(
    "geodoc1,geodoc2,start1,start2,end1,end2,result",
    [
        (  # same text, start, and end
            "1st",
            "1st",
            0,
            0,
            1,
            1,
            True,
        ),
        (  # different start
            "1st",
            "1st",
            0,
            1,
            1,
            1,
            False,
        ),
        (  # different end
            "1st",
            "1st",
            0,
            0,
            1,
            2,
            False,
        ),
        (  # underlying geodoc (text) different
            "1st",
            "2nd",
            0,
            0,
            1,
            1,
            False,
        ),
    ],
)
def test_geospan_eq(
    geodoc1: str,
    geodoc2: str,
    start1: int,
    start2: int,
    end1: int,
    end2: int,
    result: bool,
    first_geodoc: GeoDoc,
    second_geodoc: GeoDoc,
):
    geodoc = lambda x: first_geodoc if x == "1st" else second_geodoc
    assert (
        GeoSpan(geodoc(geodoc1), start1, end1) == GeoSpan(geodoc(geodoc2), start2, end2)
    ) is result


def test_geospan_location(first_geodoc: GeoDoc):
    geospan = first_geodoc.toponyms[0]
    location = geospan.location
    expected = {
        "geonameid": 3041563,
        "name": "Andorra la Vella",
        "admin2_geonameid": None,
        "admin2_name": None,
        "admin1_geonameid": 3041566,
        "admin1_name": "Andorra la Vella",
        "country_geonameid": 3041565,
        "country_name": "Andorra",
        "feature_name": "capital of a political entity",
        "latitude": 42.50779,
        "longitude": 1.52109,
        "elevation": None,
        "population": 20430,
    }
    assert type(location) is dict
    assert location == expected


def test_geospan_score(first_geodoc: GeoDoc):
    geospan = first_geodoc.toponyms[0]
    score = geospan.score
    expected = 0
    assert type(score) is float


def test_geospan_candidates(first_geodoc: GeoDoc):
    geospan = first_geodoc.toponyms[0]
    candidates = geospan.candidates
    assert type(candidates) is list
    for elem in candidates:
        assert type(elem) is int
