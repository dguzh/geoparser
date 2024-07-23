import tempfile
from pathlib import Path

import pandas as pd
import py
import pytest

from geoparser.geonames import GeoNames
from geoparser.tests.utils import get_static_test_file


@pytest.fixture(scope="session")
def test_chunk_full() -> pd.DataFrame:
    data = {"col1": [1, 2, 3], "col2": ["a", "b", "c"]}
    return pd.DataFrame.from_dict(data)


@pytest.fixture(scope="session")
def geonames_real_data() -> GeoNames:
    gazetteer = GeoNames()
    tmpdir = py.path.local(tempfile.mkdtemp())
    gazetteer.data_dir = str(
        get_static_test_file(Path("gazetteers") / Path("geonames_1000"))
    )
    gazetteer.db_path = str(tmpdir / Path(gazetteer.db_path).name)
    for dataset in gazetteer.config.data:
        gazetteer.load_data(dataset)
    return gazetteer
