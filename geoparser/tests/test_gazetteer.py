import types
import typing as t

import pytest

from geoparser.gazetteer import Gazetteer
from geoparser.tests.utils import make_concrete


@pytest.fixture
def gazetteer() -> Gazetteer:
    gazetteer = make_concrete(Gazetteer)()
    return gazetteer


@pytest.mark.parametrize(
    "template,location,expected",
    [
        (  # base case
            "<name>",
            {"name": "Geneva"},
            "Geneva",
        ),
        (  # multiple placeholders
            "<name>, <country_name>",
            {"name": "Geneva", "country_name": "Switzerland"},
            "Geneva, Switzerland",
        ),
        (  # non-ascii placeholder name
            "<XÆA12>",
            {"XÆA12": "Geneva"},
            "Geneva",
        ),
        (  # placeholder cannot contain whitespace
            "<X Æ A 12>",
            {"X Æ A 12": "Geneva"},
            "<X Æ A 12>",
        ),
        (  # remove placeholders with no value in location
            "<name>, <admin2_name>, <admin1_name>, <country_name>",
            {"name": "Geneva", "country_name": "Switzerland"},
            "Geneva, Switzerland",
        ),
        (  # no placeholder
            "I am a fish",
            {"name": "Geneva", "country_name": "Switzerland"},
            "I am a fish",
        ),
        (  # empty string
            "",
            {"name": "Geneva", "country_name": "Switzerland"},
            "",
        ),
        (  # empty location returns None
            "",
            {},
            None,
        ),
    ],
)
def test_get_location_description_base(
    gazetteer: Gazetteer,
    template: str,
    location: dict[str, str],
    expected: t.Optional[str],
):
    gazetteer.location_description_template = template
    assert gazetteer.get_location_description(location) == expected


@pytest.mark.parametrize(
    "template,location,expected",
    [
        (  # one value
            "COND[in, any{<admin2_name>, <admin1_name>, <country_name>}]",
            {"admin2_name": "Geneva"},
            "in",
        ),
        (  # all values
            "COND[in, any{<admin2_name>, <admin1_name>, <country_name>}]",
            {
                "admin2_name": "Geneva",
                "admin1_name": "Geneva",
                "country_name": "Switzerland",
            },
            "in",
        ),
        (  # no values
            "COND[in, any{<admin2_name>, <admin1_name>, <country_name>}]",
            {
                "admin3_name": "Geneva",
            },
            "",
        ),
    ],
)
def test_get_location_description_any(
    gazetteer: Gazetteer,
    template: str,
    location: dict[str, str],
    expected: t.Optional[str],
):
    gazetteer.location_description_template = template
    assert gazetteer.get_location_description(location) == expected


@pytest.mark.parametrize(
    "template,location,expected",
    [
        (  # one value
            "COND[in, all{<admin2_name>, <admin1_name>, <country_name>}]",
            {"admin2_name": "Geneva"},
            "",
        ),
        (  # all values
            "COND[in, all{<admin2_name>, <admin1_name>, <country_name>}]",
            {
                "admin2_name": "Geneva",
                "admin1_name": "Geneva",
                "country_name": "Switzerland",
            },
            "in",
        ),
        (  # no values
            "COND[in, all{<admin2_name>, <admin1_name>, <country_name>}]",
            {
                "admin3_name": "Geneva",
            },
            "",
        ),
    ],
)
def test_get_location_description_all(
    gazetteer: Gazetteer,
    template: str,
    location: dict[str, str],
    expected: t.Optional[str],
):
    gazetteer.location_description_template = template
    assert gazetteer.get_location_description(location) == expected


@pytest.mark.parametrize(
    "cond_expr",
    [
        "COND[in, sorted{<admin2_name>, <admin1_name>, <country_name>}]",  # not a supported function
        "<country_name>}",  # no condition
        "",  # empty string
    ],
)
def test_evaluate_conditionals_no_condition(
    gazetteer: Gazetteer,
    cond_expr: str,
):
    assert gazetteer.evaluate_conditionals(cond_expr) == (None, None)


@pytest.mark.parametrize(
    "cond_expr,pos,neg",
    [
        (  # all
            "COND[in, all{<admin2_name>, <admin1_name>, <country_name>}]",
            {
                "admin2_name": "Geneva",
                "admin1_name": "Geneva",
                "country_name": "Switzerland",
            },
            {
                "admin1_name": "Geneva",
                "country_name": "Switzerland",
            },
        ),
        (  # any
            "COND[in, any{<admin2_name>, <admin1_name>, <country_name>}]",
            {
                "admin2_name": "Geneva",
                "admin1_name": "Geneva",
                "country_name": "Switzerland",
            },
            {
                "asdf": "Geneva",
                "adsf": "Switzerland",
            },
        ),
    ],
)
def test_evaluate_conditionals_valid(
    gazetteer: Gazetteer,
    cond_expr: str,
    pos: dict[str, str],
    neg: dict[str, str],
):
    text, conditional_func = gazetteer.evaluate_conditionals(cond_expr)
    assert type(text) is str
    assert type(conditional_func) is types.FunctionType
    assert conditional_func(pos) is True
    assert conditional_func(neg) is False


@pytest.mark.parametrize(
    "template,location,expected",
    [
        (  # base case
            "COND[in, any{<admin2_name>, <admin1_name>, <country_name>}]",
            {"admin2_name": "Geneva"},
            "in",
        ),
        (  # does not substitute anything else
            "asdfCOND[in, any{<admin2_name>, <admin1_name>, <country_name>}]asdf",
            {
                "admin2_name": "Geneva",
                "admin1_name": "Geneva",
                "country_name": "Switzerland",
            },
            "asdfinasdf",
        ),
        (  # no conditional
            "asdf",
            {
                "admin3_name": "Geneva",
            },
            "asdf",
        ),
        (  # empty string
            "",
            {
                "admin3_name": "Geneva",
            },
            "",
        ),
        (  # empty location
            "asdf",
            {},
            "asdf",
        ),
    ],
)
def test_substitute_conditionals(
    gazetteer: Gazetteer,
    template: str,
    location: dict[str, str],
    expected: t.Optional[str],
):
    assert gazetteer.substitute_conditionals(location, template) == expected
