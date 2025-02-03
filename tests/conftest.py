import copy
import tempfile
from pathlib import Path

import py
import pytest
from pydantic import BaseModel
from sqlmodel import Session as DBSession
from sqlmodel import SQLModel
from sqlmodel.pool import StaticPool

from geoparser.annotator.db.crud import SessionRepository
from geoparser.annotator.db.db import create_engine
from geoparser.annotator.db.models import SessionCreate
from geoparser.gazetteers import GeoNames, SwissNames3D
from geoparser.geodoc import GeoDoc
from geoparser.geoparser import Geoparser
from geoparser.trainer import GeoparserTrainer
from tests.utils import get_static_test_file


class MockEntity(BaseModel):
    text: str
    start_char: int
    end_char: int


@pytest.fixture(scope="function")
def test_db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with DBSession(engine) as session:
        yield session


@pytest.fixture(scope="session")
def monkeymodule():
    with pytest.MonkeyPatch.context() as mp:
        yield mp


@pytest.fixture(scope="session")
def radio_andorra_id() -> str:
    return "3039328"


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
def geonames_real_data(monkeymodule) -> GeoNames:
    # skip download for tests
    monkeymodule.setattr(GeoNames, "_download_file", lambda *args, **kwargs: None)
    # skip deleting downloaded files
    monkeymodule.setattr(GeoNames, "_delete_file", lambda *args, **kwargs: None)
    # do not delete test files
    monkeymodule.setattr(GeoNames, "clean_dir", lambda *args, **kwargs: None)
    gazetteer = GeoNames()
    tmpdir = py.path.local(tempfile.mkdtemp())
    gazetteer.data_dir = str(
        get_static_test_file(Path("gazetteers") / Path("geonames_1000"))
    )
    gazetteer.db_path = str(tmpdir / Path(gazetteer.db_path).name)
    gazetteer.setup_database()
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
        get_static_test_file(Path("gazetteers") / Path("swissnames_subset"))
    )
    gazetteer.db_path = str(tmpdir / Path(gazetteer.db_path).name)
    return gazetteer


@pytest.fixture(scope="session")
def trainer_real_data(geonames_real_data: GeoNames) -> Geoparser:
    trainer_real_data = GeoparserTrainer(
        spacy_model="en_core_web_sm",
        transformer_model="dguzh/geo-all-MiniLM-L6-v2",
        gazetteer="geonames",
    )
    trainer_real_data.gazetteer = geonames_real_data
    return trainer_real_data


@pytest.fixture
def test_session(test_db: DBSession):
    """Fixture to create a session for testing CRUD operations."""
    session_create = SessionCreate(gazetteer="geonames")
    return SessionRepository.create(test_db, session_create)


@pytest.fixture(scope="function")
def geoparser_mocked_nlp(geoparser_real_data: Geoparser, monkeypatch):
    """Mocks the geoparser's NLP processing to return predefined toponyms."""
    mock_toponym = MockEntity(text="Andorra", start_char=0, end_char=6)

    class MockDoc:
        def __init__(self):
            self.toponyms = [mock_toponym]

    class MockNLP:
        def __call__(self, text):
            return MockDoc()

    mock_nlp = MockNLP()
    local_geoparser = copy.copy(geoparser_real_data)
    monkeypatch.setattr(local_geoparser, "nlp", mock_nlp)
    monkeypatch.setattr(local_geoparser, "setup_spacy", lambda model: mock_nlp)
    return local_geoparser
