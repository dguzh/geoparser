import pytest
from spacy.tokens import Span

from geoparser.geodoc import GeoDoc
from geoparser.geoparser import Geoparser
from geoparser.geospan import GeoSpan

sents = [
    "This here is seven tokens.",  # 7 tokens
    "This is six tokens.",  # 6 tokens
    "Roc Meler is a peak in Andorra.",  # 10 tokens
    "This is six tokens.",  # 6 tokens
    "This here is seven tokens.",  # 7 tokens
]


@pytest.fixture(scope="session")
def first_geodoc(geodocs: list[GeoDoc]) -> GeoDoc:
    return geodocs[0]


@pytest.fixture(scope="session")
def second_geodoc(geodocs: list[GeoDoc]) -> GeoDoc:
    return geodocs[1]


@pytest.fixture(scope="session")
def geodoc_long_context(geoparser_real_data: Geoparser):
    texts = [" ".join(sents)]
    docs = geoparser_real_data.parse(texts)
    return docs[0]


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
        "geonameid": "3039328",
        "name": "Radio Andorra",
        "admin2_geonameid": None,
        "admin2_name": None,
        "admin1_geonameid": "3040684",
        "admin1_name": "Encamp",
        "country_geonameid": "3041565",
        "country_name": "Andorra",
        "feature_type": "radio station",
        "latitude": 42.5282,
        "longitude": 1.57089,
        "elevation": None,
        "population": 0,
    }
    assert type(location) is dict
    assert location == expected


def test_geospan_score(first_geodoc: GeoDoc):
    geospan = first_geodoc.toponyms[0]
    score = geospan.score
    assert type(score) is float


def test_geospan_candidates(first_geodoc: GeoDoc):
    geospan = first_geodoc.toponyms[0]
    candidates = geospan.candidates
    assert type(candidates) is list
    for elem in candidates:
        assert type(elem) is str


@pytest.mark.parametrize(
    "token_limit,expected",
    [
        (11, " ".join([sents[2]])),  # fits perfectly
        (12, " ".join([sents[2]])),  # not enough for an additional sent
        (  # one additional sent possible: prefix is added first
            17,
            " ".join(sents[1:3]),
        ),
        (  # not enough for an additional suffix sent
            18,
            " ".join(sents[1:3]),
        ),
        (  # prefix and suffix possible
            23,
            " ".join(sents[1:4]),
        ),
        (  # not enough for an additional prefix sent
            24,
            " ".join(sents[1:4]),
        ),
        (  # one additional sent possible: prefix is added first
            31,
            " ".join(sents[0:4]),
        ),
        (  # not enough for an additional suffix
            32,
            " ".join(sents[0:4]),
        ),
        (  # two prefix and suffix sents each possible
            38,
            " ".join(sents),
        ),
        (  # whole segment as context
            1000,
            " ".join(sents),
        ),
    ],
)
def test_geospan_context(
    geodoc_long_context: GeoDoc, token_limit: int, expected: str, monkeypatch
):
    monkeypatch.setattr(
        "geoparser.geoparser.geoparser.SentenceTransformer.get_max_seq_length",
        lambda _: token_limit,
    )
    geospan = geodoc_long_context.toponyms[0]
    context = geospan.context
    assert type(context) is Span
    assert context.text == expected
