"""
Database fixtures for testing.

Provides function-scoped in-memory test databases configured exactly like production.
Each test gets a completely fresh database, ensuring perfect isolation.
"""

from unittest.mock import patch

import pytest
from sqlalchemy import Engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

import geoparser.db.models  # noqa: F401 - Ensure models are registered


@pytest.fixture(scope="function")
def test_engine() -> Engine:
    """
    Create a fresh in-memory test database for each test.

    Each test gets its own isolated database engine configured exactly like
    production (with SpatiaLite). The global event listener `_set_sqlite_pragma`
    in geoparser.db.db automatically applies to ALL Engine instances, so
    foreign keys and SpatiaLite are configured without any extra setup.

    Since SpatiaLite initialization is fast (<0.01s), the overhead is minimal
    while providing perfect test isolation.

    Returns:
        SQLAlchemy Engine instance with in-memory database and SpatiaLite
    """
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    # Global event listeners from geoparser.db.db apply automatically
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture(scope="function")
def test_session() -> Session:
    """
    Provide a database session for tests that need one.

    This fixture uses the real `get_session()` function, which automatically
    uses the test database thanks to the `patch_db` fixture. This ensures
    we're testing the actual code path that production uses.

    Yields:
        SQLModel Session for database operations
    """
    from geoparser.db.db import get_session

    with get_session() as session:
        yield session


@pytest.fixture(scope="function", autouse=True)
def patch_db(test_engine: Engine):
    """
    Automatically redirect all database access to use the test database.

    This fixture runs automatically for every test function. By patching
    `engine` in geoparser.db.db, we ensure that:
    - Direct access to `engine` uses the test engine
    - `get_session()` works correctly (uses engine internally)
    - `get_connection()` works correctly (uses engine internally)

    Since we use `get_connection()` and `get_session()` instead of direct
    `engine` access, all database operations transparently use the test
    database at runtime.

    Args:
        test_engine: The test database engine

    Yields:
        None (patches are active during the test)
    """
    with patch("geoparser.db.db.engine", test_engine):
        yield
