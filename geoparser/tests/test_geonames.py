import typing as t
from pathlib import Path

import pandas as pd
import py
import pytest

from geoparser.geonames import GeoNames
from geoparser.tests.utils import get_static_test_file


@pytest.fixture
def geonames(tmpdir: py.path.LocalPath) -> GeoNames:
    gazetteer = GeoNames()
    gazetteer.data_dir = str(tmpdir)
    gazetteer.db_path = str(tmpdir / Path(gazetteer.db_path).name)
    return gazetteer


def test_read_file(geonames: GeoNames, test_chunk_full: pd.DataFrame):
    test_chunk_full["col1"] = test_chunk_full["col1"].astype(str)
    file_content = [
        df
        for df in geonames.read_file(
            get_static_test_file("test.tsv"),
            ["col1", "col2"],
        )
    ]
    assert file_content[0].equals(test_chunk_full)


def test_read_tsv(geonames: GeoNames, test_chunk_full: pd.DataFrame):
    test_chunk_full["col1"] = test_chunk_full["col1"].astype(str)
    file_content = [
        df
        for df in geonames.read_tsv(
            get_static_test_file("test.tsv"),
            ["col1", "col2"],
        )
    ]
    assert file_content[0].equals(test_chunk_full)


@pytest.mark.parametrize(
    "toponym,country_filter,feature_filter,expected",
    [
        ("Roc Meler", None, None, [2994701]),  # exists in data
        ("Roc Meler", ["AD"], None, [2994701]),  # country filter OK (single)
        ("Roc Meler", ["AD", "UZ"], None, [2994701]),  # country filter OK (multiple)
        ("Roc Meler", ["UZ"], None, []),  # country filter NOK
        ("Roc Meler", None, ["T"], [2994701]),  # feature filter OK (single)
        (
            "Roc Meler",
            None,
            ["T", "V"],
            [2994701],
        ),  # feature filter OK (multiple)
        ("Roc Meler", None, ["V"], []),  # feature filter NOK
    ],
)
def test_query_candidates(
    geonames_real_data: GeoNames,
    toponym: str,
    country_filter: t.Optional[list[str]],
    feature_filter: t.Optional[list[str]],
    expected: list[int],
):
    candidates = geonames_real_data.query_candidates(
        toponym, country_filter=country_filter, feature_filter=feature_filter
    )
    assert candidates == expected


@pytest.mark.parametrize(
    "location_ids,expected",
    [
        (  # location_id in db
            [2994701],
            [
                {
                    "geonameid": 2994701,
                    "name": "Roc Meler",
                    "admin2_geonameid": None,
                    "admin2_name": None,
                    "admin1_geonameid": 3041203,
                    "admin1_name": "Canillo",
                    "country_geonameid": 3041565,
                    "country_name": "Andorra",
                    "feature_name": "peak",
                    "latitude": 42.58765,
                    "longitude": 1.7418,
                    "elevation": 2811,
                    "population": 0,
                }
            ],
        ),
        ([1], [None]),  # location_id not in db
    ],
)
def test_query_location_info(
    geonames_real_data: GeoNames,
    location_ids: list[int],
    expected: list[dict],
):
    info = geonames_real_data.query_location_info(location_ids=location_ids)
    for actual, expected in zip(info, expected):
        assert actual == expected
