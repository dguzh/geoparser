from sqlmodel import Session as DBSession

from geoparser.annotator.db.crud.base import BaseRepository
from geoparser.annotator.db.models.toponym import (
    Toponym,
    ToponymCreate,
    ToponymGet,
    ToponymUpdate,
)


class SessionRepository(BaseRepository):
    def __init__(self):
        model = Toponym

    def create(self, db: DBSession, item: ToponymCreate) -> ToponymGet:
        return super().create(db, item)

    def read(self, db: DBSession, item: ToponymGet) -> ToponymGet:
        return super().read(db, item)

    def read_all(self, db: DBSession) -> list[ToponymGet]:
        return super().read_all(db)

    def update(self, db: DBSession, item: ToponymUpdate) -> ToponymGet:
        return super().update(db, item)

    def delete(self, db: DBSession, item: ToponymGet) -> ToponymGet:
        return super().delete(db, item)
