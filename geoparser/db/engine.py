from pathlib import Path

from appdirs import user_data_dir
from sqlalchemy import event
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel, create_engine

from .spatialite.loader import get_spatialite_path, load_spatialite_extension

# Global variable for lazy initialization
_engine = None


def get_engine():
    """
    Get the database engine, creating it lazily if needed.

    Returns:
        SQLAlchemy Engine instance configured for the geoparser database.
    """
    global _engine

    if _engine is None:
        # Ensure the parent directory exists
        db_location = Path(user_data_dir("geoparser", "")) / "geoparser.db"
        db_location.parent.mkdir(parents=True, exist_ok=True)
        sqlite_url = f"sqlite:///{db_location}"

        # Use NullPool for SQLite to avoid connection pool exhaustion
        _engine = create_engine(
            sqlite_url,
            echo=False,
            poolclass=NullPool,
            connect_args={"check_same_thread": False},  # Allow multi-threaded access
        )

        # Register event listeners
        @event.listens_for(_engine, "connect")
        def enable_foreign_keys(dbapi_connection, connection_record):
            """
            Enable foreign keys in the database connection.

            Args:
                dbapi_connection: SQLite database connection object.
                connection_record: SQLAlchemy connection record (unused).
            """
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        @event.listens_for(_engine, "connect")
        def enable_spatialite(dbapi_connection, connection_record):
            """
            Load the spatialite extension into the database connection.

            Args:
                dbapi_connection: SQLite database connection object.
                connection_record: SQLAlchemy connection record (unused).
            """
            spatialite_path = get_spatialite_path()

            if spatialite_path is None:
                raise RuntimeError("SpatiaLite library not found.")

            try:
                load_spatialite_extension(dbapi_connection, spatialite_path)
            except Exception as e:
                raise RuntimeError(f"Failed to load SpatiaLite extension: {e}") from e

        # Create tables if they don't exist
        SQLModel.metadata.create_all(_engine)

    return _engine


# Export engine for direct use - it will be created lazily when accessed
engine = type(
    "LazyEngine", (), {"__getattr__": lambda self, name: getattr(get_engine(), name)}
)()
