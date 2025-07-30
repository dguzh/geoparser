import typing as t
from pathlib import Path

from appdirs import user_data_dir
from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

from .spatialite.loader import get_spatialite_path, load_spatialite_extension

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
        raise RuntimeError("SpatiaLite library not found.")

    try:
        load_spatialite_extension(dbapi_connection, spatialite_path)
    except Exception as e:
        raise RuntimeError(f"Failed to load SpatiaLite extension: {e}") from e


def create_db_and_tables(engine):
    SQLModel.metadata.create_all(engine)


def get_db() -> t.Iterator[Session]:
    db = Session(engine)
    try:
        yield db
    finally:
        db.close()


create_db_and_tables(engine)
