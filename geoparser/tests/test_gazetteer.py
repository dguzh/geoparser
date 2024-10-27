import sqlite3
import tempfile
import typing as t
from pathlib import Path

import pandas as pd
import py
import pytest
from requests_mock.mocker import Mocker

from geoparser.config.models import Column, GazetteerData
from geoparser.gazetteer import LocalDBGazetteer
from geoparser.geonames import GeoNames
from geoparser.tests.utils import get_static_test_file, make_concrete


def check_table_creation(
    gazetteer: t.Type[LocalDBGazetteer], table_name: str, method: str, *args, **kwargs
):
    """
    helper function for checking if a table has been created properly.

    provide LocalDBGazetteer (subclass) instance, a table name and
    the instance method for creating the table. any number of args
    and kwargs can be added.
    """
    # 1. table does not exist before creation
    tables_query = "SELECT name FROM sqlite_master"
    gazetteer._initiate_connection()
    cursor = gazetteer._get_cursor()
    tables_before = cursor.execute(tables_query).fetchall()
    assert tables_before == [] or table_name not in tables_before[0]
    # 2. create table with specified method
    getattr(gazetteer, method)(*args, **kwargs)
    # 3. table exists after creation
    tables_after = cursor.execute(tables_query).fetchall()
    assert len(tables_after) > len(tables_before) and table_name in tables_after[0]


def check_table_population(
    gazetteer: t.Type[LocalDBGazetteer],
    table_name: str,
    method: str,
    expected_first_row: tuple[any, ...],
    *args,
    **kwargs,
):
    """
    helper function for checking if a table has been populated properly.

    provide LocalDBGazetteer (subclass) instance, a table name and
    the instance method for populating the table. the function checks
    if the expected first row has been added to the table. any number
    of args and kwargs can be added.
    """
    # 1. table is empty before populating it
    rows_query = f"SELECT * FROM {table_name}"
    gazetteer._initiate_connection()
    cursor = gazetteer._get_cursor()
    rows_before = cursor.execute(rows_query).fetchall()
    assert rows_before == []
    # 2. populating the table with specified method
    getattr(gazetteer, method)(*args, **kwargs)
    # 3. table contains a specific first row
    rows_after = cursor.execute(rows_query).fetchall()
    assert len(rows_after) > 0
    assert rows_after[0] == expected_first_row


@pytest.fixture(scope="function")
def localdb_gazetteer(monkeypatch) -> LocalDBGazetteer:
    monkeypatch.setattr(
        "geoparser.config.config.get_config_file",
        lambda _: get_static_test_file("gazetteers_config_valid.yaml"),
    )
    localdb_gazetteer = make_concrete(LocalDBGazetteer)(gazetteer_name="test-full")
    tmpdir = py.path.local(tempfile.mkdtemp())
    localdb_gazetteer.data_dir = str(tmpdir)
    localdb_gazetteer.db_path = str(tmpdir / Path(localdb_gazetteer.db_path).name)
    localdb_gazetteer.clean_dir()
    return localdb_gazetteer


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
    "dataset",
    [
        GazetteerData(
            name="a",
            url="https://my.url.org/path/to/a.txt",
            extracted_files=["a.txt"],
            columns=[Column(name="", type="")],
        ),
        GazetteerData(
            name="b",
            url="https://my.url.org/path/to/b.zip",
            extracted_files=["b.txt"],
            columns=[Column(name="", type="")],
        ),
    ],
)
def test_download_file(
    localdb_gazetteer: LocalDBGazetteer,
    dataset: GazetteerData,
    requests_mock: Mocker,
):
    raw_file = dataset.url.split("/")[-1]
    with open(get_static_test_file(raw_file), "rb") as file:
        requests_mock.get(dataset.url, body=file)
        localdb_gazetteer.download_file(dataset=dataset)
    dir_content = Path(localdb_gazetteer.db_path).parent.glob("**/*")
    files = [content.name for content in dir_content]
    # a.txt downloaded as is, b.zip has been extracted and is still around
    zipfile = [raw_file] if raw_file.endswith(".zip") else []
    assert sorted(files) == sorted(dataset.extracted_files + zipfile)


def test_create_data_table(geonames_patched: GeoNames):
    table_data = geonames_patched.config.data[0]
    check_table_creation(
        geonames_patched, table_data.name, "create_data_table", table_data
    )


def test_populate_data_table(geonames_patched: GeoNames):
    table_data = geonames_patched.config.data[0]
    # setup: create table
    geonames_patched.create_data_table(table_data)
    # actual test: table is empty at first, then contains a specific row
    expected_first_row = (
        2994701,
        "Roc Meler",
        "Roc Meler",
        "Roc Mele,Roc Meler,Roc Mélé",
        42.58765,
        1.7418,
        "T",
        "PK",
        "AD",
        "AD,FR",
        "02",
        None,
        None,
        None,
        0,
        2811,
        2348,
        "Europe/Andorra",
        "2023-10-03",
    )
    check_table_population(
        geonames_patched,
        table_data.name,
        "populate_data_table",
        expected_first_row,
        table_data,
    )


def test_create_names_table(geonames_patched: GeoNames):
    check_table_creation(geonames_patched, "names", "create_names_table")


def test_populate_names_table(geonames_patched: GeoNames):
    # setup: create tables from previous steps
    for dataset in geonames_patched.config.data:
        geonames_patched.load_data(dataset)
    geonames_patched.create_names_table()
    # actual test: table is empty at first, then contains a specific row
    expected_first_row = (
        1,
        2994701,
        "Roc Meler",
    )
    check_table_population(
        geonames_patched,
        "names",
        "populate_names_table",
        expected_first_row,
    )


def test_create_names_fts_table(geonames_patched: GeoNames):
    check_table_creation(geonames_patched, "names_fts", "create_names_fts_table")


def test_populate_names_fts_table(geonames_patched: GeoNames):
    # setup: create tables from previous steps
    for dataset in geonames_patched.config.data:
        geonames_patched.load_data(dataset)
    geonames_patched.create_names_table()
    geonames_patched.populate_names_table()
    geonames_patched.create_names_fts_table()
    # 1. table has some rows before populating it further
    rows_query = f"SELECT * FROM names_fts"
    geonames_patched._initiate_connection()
    cursor = geonames_patched._get_cursor()
    rows_before = cursor.execute(rows_query).fetchall()
    # 2. populating the table with specified method
    geonames_patched.populate_names_fts_table()
    # 3. there are no changes to table rows
    rows_after = cursor.execute(rows_query).fetchall()
    assert rows_before == rows_after


def test_create_locations_table(geonames_patched: GeoNames):
    check_table_creation(geonames_patched, "locations", "create_locations_table")


def test_drop_redundant_tables(geonames_patched: GeoNames):
    # setup: create tables from previous steps
    for dataset in geonames_patched.config.data:
        geonames_patched.load_data(dataset)
    geonames_patched.create_names_table()
    geonames_patched.populate_names_table()
    geonames_patched.create_names_fts_table()
    geonames_patched.populate_names_fts_table()
    geonames_patched.create_locations_table()
    geonames_patched.populate_locations_table()
    # 1. all data tables are redundant
    redundant_tables = [dataset.name for dataset in geonames_patched.config.data]
    tables_query = "SELECT name FROM sqlite_master"
    geonames_patched._initiate_connection()
    cursor = geonames_patched._get_cursor()
    geonames_patched._commit()
    # 2. removing redundant tables
    geonames_patched.drop_redundant_tables()
    # all redundant tables have been dropped
    tables_after = cursor.execute(tables_query).fetchall()[0]
    assert all([table not in tables_after for table in redundant_tables])


def test_query_candidates(geonames_real_data: GeoNames, radio_andorra_id: int):
    toponym = "Andorra"
    assert geonames_real_data.query_candidates(toponym) == [radio_andorra_id]


def test_query_location_info(geonames_real_data: GeoNames, radio_andorra_id: int):
    print(geonames_real_data.query_location_info([radio_andorra_id]))
    expected_info = {
        "geonameid": "3039328",
        "name": "Radio Andorra",
        "feature_type": "radio station",
        "latitude": 42.5282,
        "longitude": 1.57089,
        "elevation": None,
        "population": 0,
        "admin2_geonameid": None,
        "admin2_name": None,
        "admin1_geonameid": "3040684",
        "admin1_name": "Encamp",
        "country_geonameid": "3041565",
        "country_name": "Andorra",
    }
    assert geonames_real_data.query_location_info([radio_andorra_id]) == [expected_info]


def test_initiate_connection(localdb_gazetteer: LocalDBGazetteer):
    localdb_gazetteer._initiate_connection()
    assert type(localdb_gazetteer._local.conn) == sqlite3.Connection


def test_close_connection(localdb_gazetteer: LocalDBGazetteer):
    localdb_gazetteer._initiate_connection()
    localdb_gazetteer._close_connection()
    # Check that connection is None after being closed
    assert localdb_gazetteer._local.conn is None


def test_get_cursor(localdb_gazetteer: LocalDBGazetteer):
    localdb_gazetteer._initiate_connection()
    assert type(localdb_gazetteer._get_cursor()) == sqlite3.Cursor


def test_execute_query(localdb_gazetteer: LocalDBGazetteer):
    query1 = "CREATE TABLE IF NOT EXISTS asdf (asdf TEXT)"
    query2 = "SELECT name FROM sqlite_master"
    localdb_gazetteer.execute_query(query1)
    tables = [table for table in localdb_gazetteer.execute_query(query2)[0]]
    assert ["asdf"] == tables
