import typing as t
from contextlib import contextmanager

import pytest
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.sql import text
from sqlmodel import Session, create_engine, select

from geoparser.annotator.db.db import create_db_and_tables, enable_foreign_keys, get_db
from geoparser.annotator.db.models import Document

TEST_SQLITE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="module")
def test_engine() -> t.Iterator[Engine]:
    test_engine = create_engine(TEST_SQLITE_URL, echo=False)
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def session(test_engine: Engine) -> t.Iterator[Session]:
    with Session(test_engine) as session:
        yield session


@pytest.fixture
def mock_get_db(monkeypatch):
    @contextmanager
    def mock_get_db_func():
        session = Session(TEST_SQLITE_URL)
        try:
            yield session
        finally:
            session.close()

    monkeypatch.setattr("geoparser.annotator.db.db.get_db", mock_get_db_func)
    return mock_get_db_func


def test_enable_foreign_keys(test_engine: Engine):
    # Register the event listener for the test engine
    event.listen(test_engine, "connect", enable_foreign_keys)
    # Trigger the event listener by establishing a connection to the database
    with test_engine.connect() as connection:
        result = connection.execute(text("PRAGMA foreign_keys"))
        foreign_keys_enabled = result.scalar()
        # 1 confirms foreign keys are enabled
        assert foreign_keys_enabled == 1


def test_create_db_and_tables(test_engine: Engine):
    create_db_and_tables(test_engine)
    with test_engine.connect() as connection:
        result = connection.execute(
            text("SELECT name FROM sqlite_master WHERE type='table';")
        )
        tables = [row[0] for row in result]
        assert len(tables) > 0, "No tables were created in the database"


def test_get_db(session: Session):
    # check return type with real dependency
    assert isinstance(next(get_db()), Session)
    # select statement does not fail with mocked db dependency
    result = session.exec(select(Document)).all()


def test_get_db_with_mock(mock_get_db):
    with mock_get_db() as session:
        assert isinstance(session, Session), "Session is not of type 'Session'"
