from pathlib import Path

from appdirs import user_data_dir
from sqlalchemy import event
from sqlalchemy.orm import Query
from sqlmodel import Session, SQLModel, create_engine

from geoparser.annotator.db.models.document import Document
from geoparser.annotator.db.models.toponym import Toponym

db_location = Path(user_data_dir("geoparser", "")) / "annotator" / "annotator.db"
sqlite_url = f"sqlite:///{db_location}"

engine = create_engine(sqlite_url, echo=True)


@event.listens_for(Query, "before_compile", retval=True)
def enforce_document_order(query):
    """Ensure documents are always ordered by doc_index when queried."""
    if hasattr(query, "_entities"):
        for entity in query._entities:
            if hasattr(entity, "mapper") and entity.mapper.class_ is Document:
                query = query.order_by(Document.doc_index)
    return query


@event.listens_for(Query, "before_compile", retval=True)
def enforce_toponym_order(query):
    """Ensure toponyms are always ordered by Toponym.start when queried."""
    if hasattr(query, "_entities"):
        for entity in query._entities:
            if hasattr(entity, "mapper") and entity.mapper.class_ is Toponym:
                query = query.order_by(Toponym.start)
    return query


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_db():
    db = Session(engine)
    try:
        yield db
    finally:
        db.close()
