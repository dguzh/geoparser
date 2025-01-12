from sqlmodel import Session as DBSession

from geoparser.annotator.db.crud.base import BaseRepository
from geoparser.annotator.db.models.document import (
    Document,
    DocumentCreate,
    DocumentGet,
    DocumentUpdate,
)


class SessionRepository(BaseRepository):
    def __init__(self):
        model = Document

    def create(self, db: DBSession, item: DocumentCreate) -> DocumentGet:
        return super().create(db, item)

    def read(self, db: DBSession, item: DocumentGet) -> DocumentGet:
        return super().read(db, item)

    def read_all(self, db: DBSession) -> list[DocumentGet]:
        return super().read_all(db)

    def update(self, db: DBSession, item: DocumentUpdate) -> DocumentGet:
        return super().update(db, item)

    def delete(self, db: DBSession, item: DocumentGet) -> DocumentGet:
        return super().delete(db, item)
