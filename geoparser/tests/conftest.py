import tempfile
from pathlib import Path

import pandas as pd
import py
import pytest

from geoparser.geodoc import GeoDoc
from geoparser.geonames import GeoNames
from geoparser.geoparser import Geoparser
from geoparser.tests.utils import get_static_test_file


@pytest.fixture(scope="session")
def andorra_id() -> int:
    return 3039328


@pytest.fixture(scope="session")
def geodocs(geoparser: Geoparser) -> list[GeoDoc]:
    texts = [
        "Roc Meler is a peak in Andorra.",
        "Roc Meler is not in Germany.",
    ]
    docs = geoparser.parse(texts)
    return docs


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


@pytest.fixture(scope="session")
def geoparser() -> Geoparser:
    geoparser = Geoparser(
        spacy_model="en_core_web_sm",
        transformer_model="dguzh/geo-all-MiniLM-L6-v2",
        gazetteer="geonames",
    )
    return geoparser


@pytest.fixture(scope="session")
def test_chunk_full() -> pd.DataFrame:
    data = {"col1": [1, 2, 3], "col2": ["a", "b", "c"]}
    return pd.DataFrame.from_dict(data)
