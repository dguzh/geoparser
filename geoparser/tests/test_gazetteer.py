import re
import sqlite3
import types
import typing as t
from pathlib import Path

import pandas as pd
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
    localdb_gazetteer.clean_dir()
    return localdb_gazetteer


@pytest.fixture
def test_chunk_full() -> pd.DataFrame:
    data = {"col1": [1, 2, 3], "col2": ["a", "b", "c"]}
    return pd.DataFrame.from_dict(data)


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
        (  # empty template
            "",
            {"admin2_name": "Geneva"},
            "",
        ),
    ],
)
def test_format_location_description(
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


def test_initiate_connection(localdb_gazetteer: LocalDBGazetteer):
    localdb_gazetteer._initiate_connection()
    assert type(localdb_gazetteer.conn) == sqlite3.Connection


def test_close_connection(localdb_gazetteer: LocalDBGazetteer):
    localdb_gazetteer._initiate_connection()
    localdb_gazetteer._close_connection()
    # sqlite3.ProgrammingError is raised when committing on closed db
    with pytest.raises(sqlite3.ProgrammingError):
        localdb_gazetteer._commit()


def test_get_cursor(localdb_gazetteer: LocalDBGazetteer):
    localdb_gazetteer._initiate_connection()
    assert type(localdb_gazetteer._get_cursor()) == sqlite3.Cursor


def test_create_table(localdb_gazetteer: LocalDBGazetteer):
    dataset = localdb_gazetteer.config.data[0]
    localdb_gazetteer._create_table(dataset)
    localdb_gazetteer._initiate_connection()
    query = "SELECT name FROM sqlite_master WHERE type='table'"
    cursor = localdb_gazetteer._get_cursor()
    tables = [table for table in cursor.execute(query).fetchall()[0]]
    assert [dataset.name] == tables


def test_create_virtual_table(localdb_gazetteer: LocalDBGazetteer):
    dataset = localdb_gazetteer.config.data[0]
    localdb_gazetteer._create_virtual_table(dataset.virtual_tables[0])
    localdb_gazetteer._initiate_connection()
    query = "SELECT name FROM sqlite_master WHERE type='table' AND sql LIKE 'CREATE VIRTUAL TABLE%'"
    cursor = localdb_gazetteer._get_cursor()
    tables = [table for table in cursor.execute(query).fetchall()[0]]
    assert [dataset.virtual_tables[0].name] == tables


def test_create_tables(localdb_gazetteer: LocalDBGazetteer):
    dataset = localdb_gazetteer.config.data[0]
    localdb_gazetteer.create_tables(dataset)
    localdb_gazetteer._initiate_connection()
    tables_query = "SELECT name FROM sqlite_master WHERE type='table'"
    virtual_tables_query = "SELECT name FROM sqlite_master WHERE type='table' AND sql LIKE 'CREATE VIRTUAL TABLE%'"
    cursor = localdb_gazetteer._get_cursor()
    tables = [table for table in cursor.execute(tables_query).fetchall()[0]]
    virtual_tables = [
        table for table in cursor.execute(virtual_tables_query).fetchall()[0]
    ]
    assert [dataset.name] == tables
    assert [dataset.virtual_tables[0].name] == virtual_tables


def test_load_file_into_table(
    monkeypatch, localdb_gazetteer: LocalDBGazetteer, test_chunk_full: pd.DataFrame
):
    monkeypatch.setattr(
        LocalDBGazetteer,
        "read_file",
        lambda *_: [test_chunk_full],
    )
    dataset = localdb_gazetteer.config.data[0]
    localdb_gazetteer.create_tables(dataset)
    localdb_gazetteer.load_file_into_table(
        get_static_test_file("a.txt"),  # just needed for line count
        dataset.name,
        ["col1", "col2"],
    )
    localdb_gazetteer._initiate_connection()
    content_query = f"SELECT * FROM {dataset.name}"
    cursor = localdb_gazetteer._get_cursor()
    content = cursor.execute(content_query).fetchall()
    assert content == [tuple(row) for row in test_chunk_full.values.tolist()]


def test_populate_virtual_table(
    monkeypatch, localdb_gazetteer: LocalDBGazetteer, test_chunk_full: pd.DataFrame
):
    monkeypatch.setattr(
        LocalDBGazetteer,
        "read_file",
        lambda *_: [test_chunk_full],
    )
    dataset = localdb_gazetteer.config.data[0]
    localdb_gazetteer.create_tables(dataset)
    localdb_gazetteer.load_file_into_table(
        get_static_test_file("a.txt"),  # just needed for line count
        dataset.name,
        ["col1", "col2"],
    )
    localdb_gazetteer.populate_virtual_table(dataset.virtual_tables[0], dataset.name)
    localdb_gazetteer._initiate_connection()
    content_query = f"SELECT * FROM {dataset.virtual_tables[0].name}"
    cursor = localdb_gazetteer._get_cursor()
    content = cursor.execute(content_query).fetchall()
    assert content == [(value,) for value in test_chunk_full["col2"].to_list()]


def test_populate_tables(
    monkeypatch, localdb_gazetteer: LocalDBGazetteer, test_chunk_full: pd.DataFrame
):
    monkeypatch.setattr(
        LocalDBGazetteer,
        "read_file",
        lambda *_: [test_chunk_full],
    )
    dataset = localdb_gazetteer.config.data[0]
    localdb_gazetteer.create_tables(dataset)
    with open(Path(localdb_gazetteer.data_dir) / dataset.extracted_file, "w"):
        pass
    localdb_gazetteer.populate_tables(dataset)
    localdb_gazetteer._initiate_connection()
    content_query_full = f"SELECT * FROM {dataset.name}"
    content_query_virtual = f"SELECT * FROM {dataset.virtual_tables[0].name}"
    cursor = localdb_gazetteer._get_cursor()
    content_full = cursor.execute(content_query_full).fetchall()
    content_virtual = cursor.execute(content_query_virtual).fetchall()
    assert content_full == [tuple(row) for row in test_chunk_full.values.tolist()]
    assert content_virtual == [(value,) for value in test_chunk_full["col2"].to_list()]


def test_load_data(
    monkeypatch, localdb_gazetteer: LocalDBGazetteer, test_chunk_full: pd.DataFrame
):
    monkeypatch.setattr(
        LocalDBGazetteer,
        "read_file",
        lambda *_: [test_chunk_full],
    )
    dataset = localdb_gazetteer.config.data[0]
    with open(Path(localdb_gazetteer.data_dir) / dataset.extracted_file, "w"):
        pass
    localdb_gazetteer.load_data(dataset)
    localdb_gazetteer._initiate_connection()
    content_query_full = f"SELECT * FROM {dataset.name}"
    content_query_virtual = f"SELECT * FROM {dataset.virtual_tables[0].name}"
    cursor = localdb_gazetteer._get_cursor()
    content_full = cursor.execute(content_query_full).fetchall()
    content_virtual = cursor.execute(content_query_virtual).fetchall()
    assert content_full == [tuple(row) for row in test_chunk_full.values.tolist()]
    assert content_virtual == [(value,) for value in test_chunk_full["col2"].to_list()]


def test_execute_query(localdb_gazetteer: LocalDBGazetteer):
    dataset = localdb_gazetteer.config.data[0]
    localdb_gazetteer._create_table(dataset)
    query = "SELECT name FROM sqlite_master"
    tables = [table for table in localdb_gazetteer.execute_query(query)[0]]
    assert [dataset.name] == tables
