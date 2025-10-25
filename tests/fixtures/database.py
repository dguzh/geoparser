"""
Database fixtures for testing.

Provides function-scoped in-memory test databases configured exactly like production.
Each test gets a completely fresh database, ensuring perfect isolation without
needing transaction rollback.
"""

import pytest
from sqlalchemy import Engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from geoparser.db.engine import setup_foreign_keys, setup_spatialite


@pytest.fixture(scope="function")
def test_engine() -> Engine:
    """
    Create a fresh in-memory test database for each test.

    Each test gets its own isolated database engine configured exactly like
    production (with SpatiaLite). Since SpatiaLite initialization is now fast
    (<0.01s), the overhead is minimal while providing perfect test isolation.

    Returns:
        SQLAlchemy Engine instance with in-memory database and SpatiaLite
    """
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    setup_foreign_keys(engine)
    setup_spatialite(engine)
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture(scope="function")
def test_session(test_engine: Engine) -> Session:
    """
    Provide a database session for each test.

    Since each test gets a fresh engine, there's no need for transaction rollback -
    the entire database is discarded after the test. This provides perfect isolation
    with a simpler implementation.

    Uses expire_on_commit=False to match production patterns (e.g., Project.get_documents()).

    Args:
        test_engine: Function-scoped test database engine

    Yields:
        SQLModel Session for database operations
    """
    session = Session(bind=test_engine, expire_on_commit=False)
    yield session
    session.close()


@pytest.fixture(scope="function", autouse=True)
def patch_get_engine(test_engine, monkeypatch):
    """
    Automatically redirect get_engine() to use test_engine for all tests.

    This fixture runs automatically for every test function, ensuring that any code
    calling get_engine() will use the test database instead of the production database.

    We use monkeypatch instead of unittest.mock.patch because monkeypatch can modify
    already-imported module attributes. When modules do "from X import Y", they create
    a local binding to the function object. We must patch the function in each module's
    namespace where it was imported.

    Args:
        test_engine: The test database engine
        monkeypatch: Pytest's monkeypatch fixture
    """

    # Create a function that returns the test_engine
    def mock_get_engine():
        return test_engine

    # Patch get_engine() in every module that imports it
    # We must patch each module's local binding, not just the source
    monkeypatch.setattr("geoparser.db.models.feature.get_engine", mock_get_engine)
    monkeypatch.setattr("geoparser.gazetteer.gazetteer.get_engine", mock_get_engine)
    monkeypatch.setattr("geoparser.project.project.get_engine", mock_get_engine)
    monkeypatch.setattr("geoparser.services.recognition.get_engine", mock_get_engine)
    monkeypatch.setattr("geoparser.services.resolution.get_engine", mock_get_engine)
    monkeypatch.setattr(
        "geoparser.gazetteer.installer.installer.get_engine", mock_get_engine
    )
    monkeypatch.setattr(
        "geoparser.gazetteer.installer.stages.registration.get_engine", mock_get_engine
    )
    monkeypatch.setattr(
        "geoparser.gazetteer.installer.stages.schema.get_engine", mock_get_engine
    )
    monkeypatch.setattr(
        "geoparser.gazetteer.installer.stages.transformation.get_engine",
        mock_get_engine,
    )
    monkeypatch.setattr(
        "geoparser.gazetteer.installer.stages.indexing.get_engine", mock_get_engine
    )
    monkeypatch.setattr(
        "geoparser.gazetteer.installer.strategies.spatial.get_engine", mock_get_engine
    )
    monkeypatch.setattr(
        "geoparser.gazetteer.installer.strategies.tabular.get_engine", mock_get_engine
    )
