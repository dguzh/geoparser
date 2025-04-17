import typing as t
from pathlib import Path

from appdirs import user_data_dir
from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

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


def get_gazetteer_prefix(name: str) -> str:
    """
    Generate a deterministic table name prefix for a gazetteer.

    This function creates a consistent naming pattern for gazetteer tables
    to emulate schemas in SQLite, which doesn't support actual schemas.

    Args:
        name: Name of the gazetteer

    Returns:
        Prefix string in format 'gazetteer_{normalized_name}__'
        where normalized_name is lowercase with non-alphanumeric chars removed
    """
    # Normalize name: lowercase and remove non-alphanumeric chars
    normalized = "".join(c for c in name.lower() if c.isalnum())
    return f"gazetteer_{normalized}__"


def create_db_and_tables(engine):
    SQLModel.metadata.create_all(engine)


def get_db() -> t.Iterator[Session]:
    db = Session(engine)
    try:
        yield db
    finally:
        db.close()


create_db_and_tables(engine)
