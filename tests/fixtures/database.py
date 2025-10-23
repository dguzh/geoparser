"""
Database fixtures for testing.

Provides a single session-scoped in-memory test database configured exactly
like production. All tests share the same database engine, but each test gets
a fresh transaction that is rolled back after the test completes, ensuring
complete isolation between tests.
"""

import pytest
from sqlalchemy import Engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from geoparser.db.engine import setup_foreign_keys, setup_spatialite


@pytest.fixture(scope="session")
def test_engine() -> Engine:
    """
    Create a session-scoped in-memory test database configured like production.

    This engine includes SpatiaLite and is created ONCE for the entire test session.
    All tests share this engine, but each test gets an isolated transaction via
    the test_session fixture.

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
    Provide an isolated database session for each test.

    Creates a new connection and transaction for each test. The transaction is
    rolled back after the test completes, ensuring that changes made during the
    test do not affect other tests. This provides complete isolation while sharing
    a single database engine across all tests.

    Uses expire_on_commit=False so that ORM objects remain accessible even after
    the session commits, which matches the pattern used in production code (e.g.,
    Project.get_documents()).

    Args:
        test_engine: Session-scoped test database engine

    Yields:
        SQLModel Session for database operations
    """
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, expire_on_commit=False)

    yield session

    session.close()
    transaction.rollback()
    connection.close()
