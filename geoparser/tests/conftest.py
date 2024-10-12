import tempfile
from pathlib import Path

import pandas as pd
import py
import pytest

from geoparser.geodoc import GeoDoc
from geoparser.geonames import GeoNames
from geoparser.geoparser import Geoparser
from geoparser.swissnames3d import SwissNames3D
from geoparser.tests.utils import get_static_test_file
from geoparser.trainer import GeoparserTrainer


@pytest.fixture(scope="session")
def radio_andorra_id() -> int:
    return 3039328


@pytest.fixture(scope="session")
def geodocs(geoparser_real_data: Geoparser) -> list[GeoDoc]:
    texts = [
        "Roc Meler is a peak in Andorra.",
        "Roc Meler is not in Germany.",
    ]
    docs = geoparser_real_data.parse(texts)
    return docs


@pytest.fixture(scope="function")
def geonames_patched() -> GeoNames:
    gazetteer = GeoNames()
    tmpdir = py.path.local(tempfile.mkdtemp())
    gazetteer.data_dir = str(
        get_static_test_file(Path("gazetteers") / Path("geonames_1000"))
    )
    gazetteer.db_path = str(tmpdir / Path(gazetteer.db_path).name)
    return gazetteer


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
    gazetteer.create_names_table()
    gazetteer.populate_names_table()
    gazetteer.create_names_fts_table()
    gazetteer.populate_names_fts_table()
    gazetteer.create_locations_table()
    gazetteer.populate_locations_table()
    gazetteer.drop_redundant_tables()
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
def geoparser_real_data(geonames_real_data: GeoNames) -> Geoparser:
    geoparser_real_data = Geoparser(
        spacy_model="en_core_web_sm",
        transformer_model="dguzh/geo-all-MiniLM-L6-v2",
        gazetteer="geonames",
    )
    geoparser_real_data.gazetteer = geonames_real_data
    return geoparser_real_data


@pytest.fixture(scope="function")
def swissnames3d_patched() -> SwissNames3D:
    gazetteer = SwissNames3D()
    tmpdir = py.path.local(tempfile.mkdtemp())
    gazetteer.data_dir = str(
        get_static_test_file(Path("gazetteers") / Path("swissnames3d_1000"))
    )
    gazetteer.db_path = str(tmpdir / Path(gazetteer.db_path).name)
    return gazetteer


@pytest.fixture(scope="session")
def swissnames3d_real_data() -> SwissNames3D:
    gazetteer = SwissNames3D()
    tmpdir = py.path.local(tempfile.mkdtemp())
    gazetteer.data_dir = str(
        get_static_test_file(Path("gazetteers") / Path("swissnames3d_1000"))
    )
    gazetteer.db_path = str(tmpdir / Path(gazetteer.db_path).name)
    for dataset in gazetteer.config.data:
        gazetteer.load_data(dataset)
    gazetteer.create_names_table()
    gazetteer.populate_names_table()
    gazetteer.create_names_fts_table()
    gazetteer.populate_names_fts_table()
    gazetteer.create_locations_table()
    gazetteer.populate_locations_table()
    gazetteer.drop_redundant_tables()
    return gazetteer


@pytest.fixture(scope="session")
def test_chunk_full() -> pd.DataFrame:
    data = {"col1": [1, 2, 3], "col2": ["a", "b", "c"]}
    return pd.DataFrame.from_dict(data)


@pytest.fixture(scope="session")
def trainer_real_data(geonames_real_data: GeoNames) -> Geoparser:
    trainer_real_data = GeoparserTrainer(
        spacy_model="en_core_web_sm",
        transformer_model="dguzh/geo-all-MiniLM-L6-v2",
        gazetteer="geonames",
    )
    trainer_real_data.gazetteer = geonames_real_data
    return trainer_real_data
