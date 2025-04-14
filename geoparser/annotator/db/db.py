import typing as t
from pathlib import Path

from appdirs import user_data_dir
from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

db_location = Path(user_data_dir("geoparser", "")) / "annotator" / "annotator.db"
db_location.parent.mkdir(parents=True, exist_ok=True)
sqlite_url = f"sqlite:///{db_location}"

engine = create_engine(sqlite_url, echo=False)


@event.listens_for(engine, "connect")
def enable_foreign_keys(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def create_db_and_tables(engine):
    SQLModel.metadata.create_all(engine)


def get_db() -> t.Iterator[Session]:
    db = Session(engine)
    try:
        yield db
    finally:
        db.close()
