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

from .functions import levenshtein, soundex

# Database URL configuration (SQLite)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{Path(user_data_dir('geoparser', '')) / 'geoparser.db'}",
)

# Ensure parent directory exists
db_path = DATABASE_URL.replace("sqlite:///", "")
Path(db_path).parent.mkdir(parents=True, exist_ok=True)

# Whether new connections should be tuned for write throughput. Toggled on only
# for the duration of a gazetteer installation via the optimized_writes context
# manager.
_optimized_writes_enabled = False


# Event listener for SQLite foreign keys and fuzzy matching functions
# This applies to ALL Engine instances (including test engines)
@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    """
    Configure SQLite connections on connect.

    Enables foreign key enforcement and registers the fuzzy matching functions
    (soundex and levenshtein) for all SQLite connections. When optimized writes
    are active, additionally applies throughput-oriented PRAGMAs that trade
    durability for speed, which is acceptable during gazetteer installation
    because the process is idempotent and can be re-run on failure.

    Args:
        dbapi_connection: Database API connection object
        connection_record: SQLAlchemy connection record
    """
    if isinstance(dbapi_connection, sqlite3.Connection):
        # Enable foreign key enforcement
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")

        # Tune the connection for write throughput when enabled
        if _optimized_writes_enabled:
            cursor.execute("PRAGMA synchronous=OFF")
            cursor.execute("PRAGMA journal_mode=MEMORY")
            cursor.execute("PRAGMA temp_store=MEMORY")
            cursor.execute("PRAGMA cache_size=-1048576")  # Up to ~1 GiB of page cache
            cursor.execute("PRAGMA mmap_size=268435456")  # 256 MiB memory-mapped I/O

        cursor.close()

        # Register pure-Python fuzzy matching functions
        dbapi_connection.create_function("soundex", 1, soundex, deterministic=True)
        dbapi_connection.create_function(
            "levenshtein", 2, levenshtein, deterministic=True
        )


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

    We don't track schema versions yet, so we rely on a single feature check:
    a database that has a ``name`` table but no companion ``name_soundex`` table
    predates the current name-search schema and cannot be used as-is. A fresh
    database has neither table; an up-to-date database has both.

    Raises:
        RuntimeError: If a legacy database layout is detected.
    """
    # The schema check is SQLite-specific; skip it for any other backend.
    if engine.dialect.name != "sqlite":
        return

    with engine.connect() as connection:

        def _table_exists(name: str) -> bool:
            result = connection.execute(
                text("SELECT 1 FROM sqlite_master WHERE type='table' AND name=:name"),
                {"name": name},
            )
            return result.first() is not None

        if _table_exists("name") and not _table_exists("name_soundex"):
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

    For operations that need direct connection access (like executing
    raw SQL in installer stages). This is the preferred way to get a
    connection as it accesses the engine at runtime, respecting any
    patches applied during testing.

    Yields:
        SQLAlchemy Connection for database operations
    """
    with engine.connect() as connection:
        yield connection


@contextmanager
def optimized_writes() -> Iterator[None]:
    """
    Tune new connections for write throughput within the context manager.

    Connections opened while this context is active apply throughput-oriented
    PRAGMAs instead of the default durable settings. This is intended for
    gazetteer installation, where large volumes of data are written and the
    process can simply be re-run on failure.

    Yields:
        None
    """
    global _optimized_writes_enabled
    _optimized_writes_enabled = True
    try:
        yield
    finally:
        _optimized_writes_enabled = False
