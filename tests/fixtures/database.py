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
def patch_get_engine(test_engine):
    """
    Automatically redirect get_engine() to use test_engine for all tests.

    This fixture runs automatically for every test function, ensuring that any code
    calling get_engine() will use the test database instead of the production database.

    We patch the _engine global variable in geoparser.db.engine, which get_engine()
    checks. This is more elegant than patching get_engine() in every module that
    imports it, since all calls to get_engine() will see the patched _engine value.

    Args:
        test_engine: The test database engine

    Yields:
        None (patches are active during the test)
    """
    with patch("geoparser.db.engine._engine", test_engine):
        yield
