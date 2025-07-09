import typing as t
from pathlib import Path

from appdirs import user_data_dir
from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

from .spatialite.loader import get_spatialite_path

# Ensure the parent directory exists
db_location = Path(user_data_dir("geoparser", "")) / "geoparser.db"
db_location.parent.mkdir(parents=True, exist_ok=True)
sqlite_url = f"sqlite:///{db_location}"

engine = create_engine(sqlite_url, echo=False)


@event.listens_for(engine, "connect")
def enable_foreign_keys(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


@event.listens_for(engine, "connect")
def load_spatialite(dbapi_connection, connection_record):
    """Load the spatialite extension into the database connection."""
    spatialite_path = get_spatialite_path()

    if spatialite_path is None:
        return

    try:
        # Enable extension loading
        dbapi_connection.enable_load_extension(True)

        # Load the spatialite extension
        dbapi_connection.load_extension(str(spatialite_path))

        # Initialize spatial metadata only if it doesn't exist
        cursor = dbapi_connection.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='spatial_ref_sys'"
        )
        if not cursor.fetchone():
            cursor.execute("SELECT InitSpatialMetaData()")
        cursor.close()

    except Exception:
        pass
    finally:
        # Disable extension loading for security
        try:
            dbapi_connection.enable_load_extension(False)
        except Exception:
            pass


def create_db_and_tables(engine):
    SQLModel.metadata.create_all(engine)


def get_db() -> t.Iterator[Session]:
    db = Session(engine)
    try:
        yield db
    finally:
        db.close()


create_db_and_tables(engine)
