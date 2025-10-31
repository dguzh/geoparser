"""
Database configuration and session management.

This module provides SQLAlchemy engine, session factory, and database utilities
following SQLAlchemy best practices for the geoparser application.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from appdirs import user_data_dir
from sqlalchemy import Engine, event
from sqlalchemy.engine import Connection
from sqlalchemy.pool import NullPool
from sqlmodel import Session, SQLModel, create_engine

import geoparser.db.models  # noqa: F401

from .spatialite.loader import get_spatialite_path, load_spatialite_extension
from .spellfix.loader import get_spellfix_path, load_spellfix_extension

# Database URL configuration (SQLite)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{Path(user_data_dir('geoparser', '')) / 'geoparser.db'}",
)

# Ensure parent directory exists
db_path = DATABASE_URL.replace("sqlite:///", "")
Path(db_path).parent.mkdir(parents=True, exist_ok=True)


# Event listener for SQLite foreign keys and SpatiaLite
# This applies to ALL Engine instances (including test engines)
@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    """
    Configure SQLite connections on connect.

    Enables foreign key enforcement and loads SpatiaLite and Spellfix extensions
    for all SQLite connections.

    Args:
        dbapi_connection: Database API connection object
        connection_record: SQLAlchemy connection record
    """
    if isinstance(dbapi_connection, sqlite3.Connection):
        # Enable foreign key enforcement
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

        # Load SpatiaLite extension
        spatialite_path = get_spatialite_path()
        if spatialite_path is None:
            raise RuntimeError("SpatiaLite library not found.")

        try:
            load_spatialite_extension(dbapi_connection, spatialite_path)
        except Exception as e:
            raise RuntimeError(f"Failed to load SpatiaLite extension: {e}") from e

        # Load Spellfix extension
        spellfix_path = get_spellfix_path()
        if spellfix_path is None:
            raise RuntimeError("Spellfix library not found.")

        try:
            load_spellfix_extension(dbapi_connection, spellfix_path)
        except Exception as e:
            raise RuntimeError(f"Failed to load Spellfix extension: {e}") from e


# Create engine once at module level
engine: Engine = create_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL debugging
    connect_args={"check_same_thread": False},
    poolclass=NullPool,  # NullPool is recommended for SQLite
    pool_pre_ping=True,  # Keeps connections fresh for long-lived apps
)


def create_db_and_tables() -> None:
    """
    Create all database tables.

    Make sure all models are imported before calling this function.
    For this application, tables are created automatically at module import.
    This function is provided for explicit table creation if needed.
    """
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
