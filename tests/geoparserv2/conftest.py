import pytest
from unittest.mock import patch, MagicMock
from sqlmodel import Session as DBSession
from sqlmodel import SQLModel
from sqlmodel.pool import StaticPool

from geoparser.db.db import create_engine
from geoparser.db.models import Session, SessionCreate
from geoparser.geoparserv2.geoparserv2 import GeoparserV2


@pytest.fixture(scope="function")
def test_db():
    """Create a test database session."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with DBSession(engine) as session:
        yield session


@pytest.fixture
def test_session(test_db: DBSession):
    """Create a test session."""
    session_create = SessionCreate(name="test-session")
    session = Session(name=session_create.name)
    test_db.add(session)
    test_db.commit()
    test_db.refresh(session)
    return session


@pytest.fixture
def mock_get_db(test_db):
    """Mock the get_db function to return our test database session."""
    with patch("geoparser.geoparserv2.geoparserv2.get_db") as mock:
        mock.return_value = iter([test_db])
        yield mock


@pytest.fixture
def geoparserv2_with_existing_session(mock_get_db, test_session):
    """Create a GeoparserV2 instance with an existing session."""
    return GeoparserV2(session_name=test_session.name)


@pytest.fixture
def geoparserv2_with_new_session(mock_get_db):
    """Create a GeoparserV2 instance with a new session."""
    return GeoparserV2(session_name="new-test-session") 