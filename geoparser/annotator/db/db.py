from pathlib import Path

from appdirs import user_data_dir
from sqlmodel import Session, SQLModel, create_engine

db_location = Path(user_data_dir("geoparser", "")) / "annotator" / "annotator.db"
sqlite_url = f"sqlite:///{db_location}"

engine = create_engine(sqlite_url, echo=True)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_db():
    db = Session(engine)
    try:
        yield db
    finally:
        db.close()
