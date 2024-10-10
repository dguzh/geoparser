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
