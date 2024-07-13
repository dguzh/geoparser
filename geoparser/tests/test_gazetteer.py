import re
import types
import typing as t
from pathlib import Path

import py
import pytest
from requests_mock.mocker import Mocker

from geoparser.gazetteer import Gazetteer, LocalDBGazetteer
from geoparser.tests.utils import get_static_test_file, make_concrete


@pytest.fixture
def gazetteer() -> Gazetteer:
    gazetteer = make_concrete(Gazetteer)()
    return gazetteer


@pytest.fixture
def localdb_gazetteer(monkeypatch, tmpdir: py.path.LocalPath) -> LocalDBGazetteer:
    monkeypatch.setattr(
        "geoparser.config.config.get_config_file",
        lambda _: get_static_test_file("gazetteers_config_valid.yaml"),
    )
    localdb_gazetteer = make_concrete(LocalDBGazetteer)(db_name="test_gazetteer")
    localdb_gazetteer.data_dir = str(tmpdir)
    localdb_gazetteer.db_path = str(tmpdir / Path(localdb_gazetteer.db_path).name)
    return localdb_gazetteer


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


@pytest.mark.parametrize("keep_db", [True, False])
def test_clean_dir(localdb_gazetteer: LocalDBGazetteer, keep_db: bool):
    # create db files and other file
    with open(localdb_gazetteer.db_path, "wb"), open(
        Path(localdb_gazetteer.db_path).parent / "other.txt", "w"
    ), open(Path(localdb_gazetteer.db_path).parent / "geonames.db-journal", "w"):
        pass
    # create subdirectory
    (Path(localdb_gazetteer.db_path).parent / "subdir").mkdir(
        parents=True, exist_ok=True
    )
    # clean tmpdir
    localdb_gazetteer.clean_dir(keep_db=keep_db)
    dir_content = Path(localdb_gazetteer.db_path).parent.glob("**/*")
    n_files = len([content for content in dir_content if content.is_file()])
    n_dirs = len([content for content in dir_content if content.is_dir()])
    # only keep db file
    if keep_db:
        assert n_files == 2
    if not keep_db:
        assert n_files == 0
    # always delete subdirectories
    assert n_dirs == 0


@pytest.mark.parametrize(
    "url, filename",
    [
        ("https://my.url.org/path/to/a.txt", "a.txt"),
        ("https://my.url.org/path/to/b.zip", "b.zip"),
    ],
)
def test_download_file(
    localdb_gazetteer: LocalDBGazetteer,
    url: str,
    filename: str,
    requests_mock: Mocker,
):
    print(type(requests_mock))
    with open(get_static_test_file(filename), "rb") as file:
        requests_mock.get(url, body=file)
        localdb_gazetteer.download_file(url=url)
    dir_content = Path(localdb_gazetteer.db_path).parent.glob("**/*")
    files = [content.name for content in dir_content]
    # a.txt downloaded as is, b.zip has been extracted
    assert files == [re.sub("zip", "txt", filename)]
