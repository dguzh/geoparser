import pandas as pd
import pytest

from geoparser.geonames import GeoNames
from geoparser.tests.utils import get_static_test_file


@pytest.fixture(scope="session")
def test_chunk_tsv() -> pd.DataFrame:
    data = {"col1": [1, 2, 3], "col2": ["a", "b", "c"]}
    return pd.DataFrame.from_dict(data)


@pytest.mark.parametrize(
    "location,expected",
    [
        (  # base case
            {
                "name": "Uster",
                "feature_type": "city",
                "admin2_name": "Uster",
                "admin1_name": "Zürich",
                "country_name": "Switzerland",
            },
            "Uster (city) in Uster, Zürich, Switzerland",
        ),
        (  # country can be missing
            {
                "name": "Uster",
                "feature_type": "city",
                "admin2_name": "Uster",
                "admin1_name": "Zürich",
            },
            "Uster (city) in Uster, Zürich",
        ),
        (  # admin1 can be missing
            {
                "name": "Uster",
                "feature_type": "city",
                "admin2_name": "Uster",
                "country_name": "Switzerland",
            },
            "Uster (city) in Uster, Switzerland",
        ),
        (  # admin2 can be missing
            {
                "name": "Uster",
                "feature_type": "city",
                "admin1_name": "Zürich",
                "country_name": "Switzerland",
            },
            "Uster (city) in Zürich, Switzerland",
        ),
    ],
)
def test_create_location_description_base(
    geonames_patched: GeoNames, location: dict, expected: str
):
    actual = geonames_patched.create_location_description(location)
    assert actual == expected


@pytest.mark.parametrize(
    "location,expected",
    [
        (  # countries are not part of any further administrative divisions
            {
                "name": "Switzerland",
                "feature_type": "independent political entity",
                "country_name": "Switzerland",
            },
            "Switzerland (independent political entity)",
        ),
        (  # description for countries will not include admin1 and admin2 even if part of location
            {
                "name": "Switzerland",
                "feature_type": "independent political entity",
                "admin2_name": "asdf",
                "admin1_name": "asdf",
                "country_name": "Switzerland",
            },
            "Switzerland (independent political entity)",
        ),
        (  # first-order admin divisions are only part of a country
            {
                "name": "Zürich",
                "feature_type": "first-order administrative division",
                "country_name": "Switzerland",
            },
            "Zürich (first-order administrative division) in Switzerland",
        ),
        (  # description for first-order admin divisions will not include admin1 and admin2 even if part of location
            {
                "name": "Zürich",
                "feature_type": "first-order administrative division",
                "admin2_name": "asdf",
                "admin1_name": "Zürich",
                "country_name": "Switzerland",
            },
            "Zürich (first-order administrative division) in Switzerland",
        ),
        (  # second-order admin divisions are only part of a country and a first-order admin division
            {
                "name": "Uster",
                "feature_type": "second-order administrative division",
                "admin1_name": "Zürich",
                "country_name": "Switzerland",
            },
            "Uster (second-order administrative division) in Zürich, Switzerland",
        ),
        (  # description for second-order admin divisions will not include admin2 even if part of location
            {
                "name": "Uster",
                "feature_type": "second-order administrative division",
                "admin2_name": "asdf",
                "admin1_name": "Zürich",
                "country_name": "Switzerland",
            },
            "Uster (second-order administrative division) in Zürich, Switzerland",
        ),
    ],
)
def test_create_location_description_divisions(
    geonames_patched: GeoNames, location: dict, expected: str
):
    actual = geonames_patched.create_location_description(location)
    assert actual == expected


def test_read_file(geonames_patched: GeoNames, test_chunk_tsv: pd.DataFrame):
    test_chunk_tsv["col1"] = test_chunk_tsv["col1"].astype(str)
    file_content, n_chunks = geonames_patched.read_file(
        get_static_test_file("test.tsv"),
        ["col1", "col2"],
    )
    file_content = list(file_content)
    assert len(file_content) == n_chunks
    assert file_content[0].equals(test_chunk_tsv)


def test_populate_locations_table(geonames_patched: GeoNames):
    # setup: load data and create tables
    geonames = geonames_patched
    for dataset in geonames.config.data:
        geonames.load_data(dataset)
    geonames.create_names_table()
    geonames.populate_names_table()
    geonames.create_names_fts_table()
    geonames.populate_names_fts_table()
    geonames.create_locations_table()
    # actual test: populate locations table
    query = "SELECT * FROM locations"
    geonames._initiate_connection()
    cursor = geonames._get_cursor()
    rows = cursor.execute(query).fetchall()
    assert not rows
    geonames.populate_locations_table()
    rows = cursor.execute(query).fetchall()
    # test data has 1000 rows
    assert len(rows) == 1000
    actual_first_row = rows[0]
    expected_first_row = (
        2994701,
        "Roc Meler",
        "peak",
        42.58765,
        1.7418,
        2811,
        0,
        None,
        None,
        3041203,
        "Canillo",
        3041565,
        "Andorra",
    )
    assert actual_first_row == expected_first_row
