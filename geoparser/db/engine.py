from pathlib import Path

from appdirs import user_data_dir
from sqlalchemy import Engine, event
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel, create_engine

from .spatialite.loader import get_spatialite_path, load_spatialite_extension

# Global variable for lazy initialization
_engine = None


def setup_foreign_keys(engine: Engine) -> None:
    """
    Set up foreign key enforcement for a database engine.

    Args:
        engine: SQLAlchemy Engine instance to configure
    """

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, connection_record):
        """Enable foreign keys in the database connection."""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def setup_spatialite(engine: Engine) -> None:
    """
    Set up SpatiaLite extension loading for a database engine.

    Args:
        engine: SQLAlchemy Engine instance to configure
    """

    @event.listens_for(engine, "connect")
    def enable_spatialite(dbapi_connection, connection_record):
        """Load the spatialite extension into the database connection."""
        spatialite_path = get_spatialite_path()

        if spatialite_path is None:
            raise RuntimeError("SpatiaLite library not found.")

        try:
            load_spatialite_extension(dbapi_connection, spatialite_path)
        except Exception as e:
            raise RuntimeError(f"Failed to load SpatiaLite extension: {e}") from e


def get_engine() -> Engine:
    """
    Get the production database engine, creating it lazily if needed.

    Returns:
        SQLAlchemy Engine instance configured for the geoparser database.
    """
    global _engine

    if _engine is None:
        # Ensure the parent directory exists
        db_location = Path(user_data_dir("geoparser", "")) / "geoparser.db"
        db_location.parent.mkdir(parents=True, exist_ok=True)
        sqlite_url = f"sqlite:///{db_location}"

        # Create the engine with NullPool for SQLite
        _engine = create_engine(
            sqlite_url,
            echo=False,
            poolclass=NullPool,
            connect_args={"check_same_thread": False},
        )

        # Set up event listeners
        setup_foreign_keys(_engine)
        setup_spatialite(_engine)

        # Create tables if they don't exist
        SQLModel.metadata.create_all(_engine)

    return _engine


class _EngineProxy:
    """
    A simple proxy that delegates all attribute access to get_engine().

    This allows 'engine' to be imported and used like a normal Engine object,
    while still maintaining lazy initialization and being easily testable.
    """

    def __getattr__(self, name):
        """Delegate all attribute access to the result of get_engine()."""
        return getattr(get_engine(), name)

    def __repr__(self):
        """Return a helpful representation."""
        return f"<EngineProxy to {get_engine()!r}>"


# Export engine for direct use - it will be created lazily when accessed
# This can be imported and used like: from geoparser.db.engine import engine
engine = _EngineProxy()
