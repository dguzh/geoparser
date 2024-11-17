import sqlite3
import tempfile
import typing as t
from pathlib import Path
from difflib import get_close_matches

import py
import pytest
from requests_mock.mocker import Mocker

from geoparser.config.models import Column, GazetteerData
from geoparser.gazetteers import GeoNames
from geoparser.gazetteers.gazetteer import LocalDBGazetteer
from tests.utils import execute_query, get_static_test_file, make_concrete


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
    tables_before = execute_query(gazetteer, tables_query)
    assert tables_before == [] or table_name not in tables_before[0]
    # 2. create table with specified method
    getattr(gazetteer, method)(*args, **kwargs)
    # 3. table exists after creation
    tables_after = execute_query(gazetteer, tables_query)
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
    rows_before = execute_query(gazetteer, rows_query)
    assert rows_before == []
    # 2. populating the table with specified method
    getattr(gazetteer, method)(*args, **kwargs)
    # 3. table contains a specific first row
    rows_after = execute_query(gazetteer, rows_query)
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
        localdb_gazetteer._download_file(dataset=dataset)
    dir_content = Path(localdb_gazetteer.db_path).parent.glob("**/*")
    files = [content.name for content in dir_content]
    # a.txt downloaded as is, b.zip has been extracted and is still around
    zipfile = [raw_file] if raw_file.endswith(".zip") else []
    assert sorted(files) == sorted(dataset.extracted_files + zipfile)


def test_create_data_table(geonames_patched: GeoNames):
    table_data = geonames_patched.config.data[0]
    check_table_creation(
        geonames_patched, table_data.name, "_create_data_table", table_data
    )


def test_populate_data_table(geonames_patched: GeoNames):
    table_data = geonames_patched.config.data[0]
    # setup: create table
    geonames_patched._create_data_table(table_data)
    # actual test: table is empty at first, then contains a specific row
    expected_first_row = (
        "2994701",
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
        "_populate_data_table",
        expected_first_row,
        table_data,
    )


def test_create_names_table(geonames_patched: GeoNames):
    check_table_creation(geonames_patched, "names", "_create_names_table")


def test_populate_names_table(geonames_patched: GeoNames):
    # setup: create tables from previous steps
    for dataset in geonames_patched.config.data:
        geonames_patched._load_data(dataset)
    geonames_patched._create_names_table()
    # actual test: table is empty at first, then contains a specific row
    expected_first_row = (
        1,
        "2994701",
        "Roc Meler",
    )
    check_table_population(
        geonames_patched,
        "names",
        "_populate_names_table",
        expected_first_row,
    )


def test_create_names_fts_table(geonames_patched: GeoNames):
    check_table_creation(geonames_patched, "names_fts", "_create_names_fts_table")


def test_populate_names_fts_table(geonames_patched: GeoNames):
    # setup: create tables from previous steps
    for dataset in geonames_patched.config.data:
        geonames_patched._load_data(dataset)
    geonames_patched._create_names_table()
    geonames_patched._populate_names_table()
    geonames_patched._create_names_fts_table()
    # 1. table has some rows before populating it further
    rows_query = f"SELECT * FROM names_fts"
    rows_before = execute_query(geonames_patched, rows_query)
    # 2. populating the table with specified method
    geonames_patched._populate_names_fts_table()
    # 3. there are no changes to table rows
    rows_after = execute_query(geonames_patched, rows_query)
    assert rows_before == rows_after


def test_create_locations_table(geonames_patched: GeoNames):
    check_table_creation(geonames_patched, "locations", "_create_locations_table")


def test_drop_redundant_tables(geonames_patched: GeoNames):
    # setup: create tables from previous steps
    for dataset in geonames_patched.config.data:
        geonames_patched._load_data(dataset)
    geonames_patched._create_names_table()
    geonames_patched._populate_names_table()
    geonames_patched._create_names_fts_table()
    geonames_patched._populate_names_fts_table()
    geonames_patched._create_locations_table()
    geonames_patched._populate_locations_table()
    # 1. all data tables are redundant
    redundant_tables = [dataset.name for dataset in geonames_patched.config.data]
    tables_query = "SELECT name FROM sqlite_master"
    geonames_patched._initiate_connection()
    cursor = geonames_patched._get_cursor()
    geonames_patched._commit()
    # 2. removing redundant tables
    geonames_patched._drop_redundant_tables()
    # all redundant tables have been dropped
    tables_after = execute_query(geonames_patched, tables_query)
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


def test_get_filter_attributes(geonames_real_data: GeoNames):
    """
    Test that _get_filter_attributes returns the correct list of filterable attributes.
    """
    attributes = geonames_real_data._get_filter_attributes()
    expected_attributes = ['name', 'feature_type', 'admin2_name', 'admin1_name', 'country_name']

    assert sorted(attributes) == sorted(expected_attributes)


def test_get_filter_values(geonames_real_data: GeoNames):
    """
    Test that _get_filter_values returns correct values for an attribute.
    """
    attributes = geonames_real_data._get_filter_attributes()

    for attr in attributes:
        values = geonames_real_data._get_filter_values(attr)
        # Fetch expected values directly from the database
        expected_values = [
            row[0]
            for row in geonames_real_data.execute_query(f"SELECT value FROM {attr}_values")
        ]
        assert sorted(values) == sorted(expected_values)


def test_validate_filter(geonames_real_data: GeoNames):
    """
    Test that _validate_filter correctly validates filters.
    """
    # Valid filter
    attributes = ['feature_type', 'admin1_name', 'country_name']
    valid_filter = {}
    for attr in attributes:
        values = geonames_real_data._get_filter_values(attr)
        valid_filter[attr] = [values[0]]  # Use first valid value

    # Should not raise an exception
    geonames_real_data._validate_filter(valid_filter)

    # Invalid filter key
    invalid_filter_key = {"invalid_attribute": ["value"]}
    with pytest.raises(ValueError, match="Invalid filter keys"):
        geonames_real_data._validate_filter(invalid_filter_key)

    # Invalid filter value
    invalid_filter_value = {attributes[0]: ["invalid_value"]}
    with pytest.raises(ValueError, match="Invalid filter values"):
        geonames_real_data._validate_filter(invalid_filter_value)


def test_construct_filter_query(geonames_real_data: GeoNames):
    """
    Test that _construct_filter_query constructs the correct query and parameters.
    """
    # Valid filter
    attributes = ['feature_type', 'admin1_name', 'country_name']
    valid_filter = {}
    for attr in attributes:
        values = geonames_real_data._get_filter_values(attr)
        valid_filter[attr] = [values[0]]  # Use first valid value

    # Construct filter query
    filter_query, params = geonames_real_data._construct_filter_query(valid_filter)

    # Expected query and params
    expected_query_parts = []
    expected_params = []
    for attr, values in valid_filter.items():
        placeholders = ", ".join(["?"] * len(values))
        expected_query_parts.append(f"locations.{attr} IN ({placeholders})")
        expected_params.extend(values)
    expected_filter_query = " AND ".join(expected_query_parts)

    assert filter_query == expected_filter_query
    assert params == expected_params

    # Test caching
    filter_key = tuple(sorted((k, tuple(v)) for k, v in valid_filter.items()))
    cached_query, cached_params = geonames_real_data._filter_cache[filter_key]
    assert cached_query == filter_query
    assert cached_params == params


def test_query_candidates_with_filter(geonames_real_data: GeoNames):
    """
    Test that query_candidates returns correct candidates when a filter is applied.
    """
    toponym = "Andorra"
    # Without filter
    candidates_without_filter = geonames_real_data.query_candidates(toponym)
    assert len(candidates_without_filter) > 0

    # With filter
    filter = {"country_name": ["Andorra"]}
    candidates_with_filter = geonames_real_data.query_candidates(toponym, filter=filter)
    assert len(candidates_with_filter) > 0
    # Ensure that candidates_with_filter is a subset of candidates_without_filter
    assert set(candidates_with_filter).issubset(set(candidates_without_filter))

    # Check that all candidates have country_name 'Andorra'
    locations = geonames_real_data.query_location_info(candidates_with_filter)
    for location in locations:
        assert location["country_name"] == "Andorra"


def test_filter_cache_mechanism(geonames_real_data: GeoNames):
    """
    Test that the filter caching mechanism works as expected.
    """
    # Valid filter
    attributes = ['feature_type', 'admin1_name', 'country_name']
    valid_filter = {}
    for attr in attributes:
        values = geonames_real_data._get_filter_values(attr)
        valid_filter[attr] = [values[0]]  # Use first valid value

    # First call: should construct and cache the filter query
    filter_query1, params1 = geonames_real_data._construct_filter_query(valid_filter)
    cache_key = tuple(sorted((k, tuple(v)) for k, v in valid_filter.items()))
    assert cache_key in geonames_real_data._filter_cache

    # Second call with the same filter: should retrieve from cache
    filter_query2, params2 = geonames_real_data._construct_filter_query(valid_filter)
    assert filter_query1 == filter_query2
    assert params1 == params2

    # Modify filter slightly
    modified_filter = valid_filter.copy()
    first_attr = list(modified_filter.keys())[0]
    modified_filter[first_attr] = [modified_filter[first_attr][0], "NonExistentValue"]

    # Should raise ValueError due to invalid value
    with pytest.raises(ValueError):
        geonames_real_data._construct_filter_query(modified_filter)

    # Cache should not contain the modified filter
    modified_cache_key = tuple(sorted((k, tuple(v)) for k, v in modified_filter.items()))
    assert modified_cache_key not in geonames_real_data._filter_cache


def test_validate_filter_suggestions(geonames_real_data: GeoNames):
    """
    Test that _validate_filter provides suggestions for invalid values.
    """
    # Invalid filter value with close match
    invalid_value = "Andora"  # Misspelled 'Andorra'
    invalid_filter = {"country_name": [invalid_value]}
    with pytest.raises(ValueError) as excinfo:
        geonames_real_data._validate_filter(invalid_filter)
    assert "Invalid filter values for country_name" in str(excinfo.value)
    assert "Did you mean Andorra?" in str(excinfo.value)
    