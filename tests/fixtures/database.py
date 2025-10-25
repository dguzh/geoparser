"""
Database fixtures for testing.

Provides function-scoped in-memory test databases configured exactly like production.
Each test gets a completely fresh database, ensuring perfect isolation without
needing transaction rollback.
"""

from unittest.mock import patch

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
def patch_get_engine(request):
    """
    Automatically patch get_engine() to return test_engine for all tests.

    This fixture runs automatically for every test function, ensuring that any code
    calling geoparser.db.engine.get_engine() will receive the test database instead
    of the production database. This eliminates the need to manually patch get_engine
    in every test.

    This fixture uses pytest's request object to get the test_engine fixture,
    ensuring proper ordering and avoiding dependency issues on Windows.

    We patch both get_engine() and _engine:
    - get_engine() returns test_engine when called by the lazy proxy
    - _engine is set to None to force reinitialization (in case it was set before patching)

    Yields:
        The active patch context
    """
    # Get the test_engine fixture from the request
    test_engine = request.getfixturevalue("test_engine")

    # Patch get_engine() and reset _engine to None
    # This ensures that even if _engine was initialized before patching,
    # it will be reinitialized with our test_engine
    with patch("geoparser.db.engine.get_engine", return_value=test_engine), patch(
        "geoparser.db.engine._engine", None
    ):
        yield
