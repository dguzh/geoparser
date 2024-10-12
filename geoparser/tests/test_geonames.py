import tempfile
import typing as t
from pathlib import Path

import pandas as pd
import py
import pytest

from geoparser.geonames import GeoNames
from geoparser.tests.utils import get_static_test_file


@pytest.fixture(scope="session")
def geonames() -> GeoNames:
    tmpdir = py.path.local(tempfile.mkdtemp())
    gazetteer = GeoNames()
    gazetteer.data_dir = str(tmpdir)
    gazetteer.db_path = str(tmpdir / Path(gazetteer.db_path).name)
    return gazetteer


def test_read_file(geonames: GeoNames, test_chunk_full: pd.DataFrame):
    test_chunk_full["col1"] = test_chunk_full["col1"].astype(str)
    file_content, n_chunks = geonames.read_file(
        get_static_test_file("test.tsv"),
        ["col1", "col2"],
    )
    file_content = list(file_content)
    assert len(file_content) == n_chunks
    assert file_content[0].equals(test_chunk_full)


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
    geonames: GeoNames, location: dict, expected: str
):
    actual = geonames.create_location_description(location)
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
        (  # description for second-order admin divisions will not include admin1 and admin2 even if part of location
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
    geonames: GeoNames, location: dict, expected: str
):
    actual = geonames.create_location_description(location)
    assert actual == expected
