from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from appdirs import user_data_dir
from sqlalchemy import Engine, event, text
from sqlalchemy.engine import Connection
from sqlalchemy.pool import NullPool
from sqlmodel import Session, SQLModel, create_engine

import geoparser.db.models  # noqa: F401

# Database URL configuration (SQLite)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{Path(user_data_dir('geoparser', '')) / 'geoparser.db'}",
)

# Ensure parent directory exists
db_path = DATABASE_URL.replace("sqlite:///", "")
Path(db_path).parent.mkdir(parents=True, exist_ok=True)


# Event listener for SQLite foreign keys
# This applies to ALL Engine instances (including test engines)
@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    """
    Configure SQLite connections on connect.

    Enables foreign key enforcement for all SQLite connections.

    Args:
        dbapi_connection: Database API connection object
        connection_record: SQLAlchemy connection record
    """
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


# Create engine once at module level
engine: Engine = create_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL debugging
    connect_args={"check_same_thread": False},
    poolclass=NullPool,  # NullPool is recommended for SQLite
    pool_pre_ping=True,  # Keeps connections fresh for long-lived apps
)


def _check_database_compatibility() -> None:
    """
    Fail early if the database was created by an incompatible older version.

    Older releases stored gazetteer data (gazetteer/source/feature/name tables)
    inside this database and linked referents to it via a feature foreign key.
    Gazetteers now live in separate artifact files, so such databases cannot be
    used as-is.

    Raises:
        RuntimeError: If a legacy database layout is detected.
    """
    with engine.connect() as connection:

        def _table_exists(name: str) -> bool:
            result = connection.execute(
                text("SELECT 1 FROM sqlite_master WHERE type='table' AND name=:name"),
                {"name": name},
            )
            return result.first() is not None

        def _table_has_column(table: str, column: str) -> bool:
            result = connection.execute(
                text(f"SELECT 1 FROM pragma_table_info('{table}') WHERE name=:column"),
                {"column": column},
            )
            return result.first() is not None

        legacy_gazetteer_tables = any(
            _table_exists(name) for name in ("gazetteer", "source", "feature", "name")
        )
        legacy_referent_layout = _table_exists("referent") and not _table_has_column(
            "referent", "feature_identifier"
        )

        if legacy_gazetteer_tables or legacy_referent_layout:
            raise RuntimeError(
                "Your geoparser database was created by an older version and is not compatible "
                "with this release:\n\n"
                f"{db_path}\n\n"
                "The Irchel Geoparser is still in active development, and the database format "
                "may change between releases. There is no automatic upgrade path yet, so you "
                "will need to delete the database file and reinstall the gazetteers to continue. "
                "Doing so also removes any projects and results stored in the database. "
            )


def create_db_and_tables() -> None:
    """
    Create all database tables.

    Make sure all models are imported before calling this function.
    For this application, tables are created automatically at module import.
    This function is provided for explicit table creation if needed.
    """
    _check_database_compatibility()
    SQLModel.metadata.create_all(engine)


@contextmanager
def get_session() -> Iterator[Session]:
    """
    Get a database session using context manager pattern.

    This is the preferred way to get a database session. The session
    is automatically closed when the context exits.

    Yields:
        SQLModel Session for database operations
    """
    session = Session(engine, expire_on_commit=False)
    try:
        yield session
    finally:
        session.close()


@contextmanager
def get_connection() -> Iterator[Connection]:
    """
    Get a database connection using context manager pattern.

    For operations that need direct connection access (like executing raw
    SQL). This is the preferred way to get a connection as it accesses the
    engine at runtime, respecting any patches applied during testing.

    Yields:
        SQLAlchemy Connection for database operations
    """
    with engine.connect() as connection:
        yield connection
