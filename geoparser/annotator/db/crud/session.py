from sqlmodel import Session as DBSession

from geoparser.annotator.db.crud.base import BaseRepository
from geoparser.annotator.db.models.session import (
    Session,
    SessionCreate,
    SessionGet,
    SessionUpdate,
)


class SessionRepository(BaseRepository):
    def __init__(self):
        model = Session

    def create(self, db: DBSession, item: SessionCreate) -> SessionGet:
        return super().create(db, item)

    def read(self, db: DBSession, item: SessionGet) -> SessionGet:
        return super().read(db, item)

    def read_all(self, db: DBSession) -> list[SessionGet]:
        return super().read_all(db)

    def update(self, db: DBSession, item: SessionUpdate) -> SessionGet:
        return super().update(db, item)

    def delete(self, db: DBSession, item: SessionGet) -> SessionGet:
        return super().delete(db, item)
