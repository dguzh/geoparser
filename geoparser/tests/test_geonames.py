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
