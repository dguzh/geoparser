import typing as t

from pydantic_core import PydanticCustomError
from sqlmodel import Session as DBSession
from sqlmodel import select

from geoparser.annotator.db.crud.base import BaseRepository
from geoparser.annotator.db.models.toponym import (
    Toponym,
    ToponymCreate,
    ToponymGet,
    ToponymUpdate,
)


class ToponymRepository(BaseRepository):
    def __init__(self):
        self.model = Toponym

    def validate_overlap(self, db: DBSession, toponym: ToponymCreate) -> bool:
        overlapping = db.exec(
            select(Toponym)
            .where(Toponym.document_id == toponym.document_id)
            .where((Toponym.start <= toponym.end) & (Toponym.end >= toponym.start))
        ).all()
        if overlapping:
            raise PydanticCustomError(
                "overlapping_toponyms",
                f"Toponyms overlap: {overlapping}",
            )
        return True

    def create(self, db: DBSession, item: ToponymCreate) -> ToponymGet:
        self.validate_overlap(item)
        return super().create(db, item)

    def upsert(
        self,
        db: DBSession,
        item: t.Union[ToponymCreate, ToponymUpdate],
        match_keys: t.List[str] = ["id"],
    ) -> ToponymGet:
        self.validate_overlap(item)
        return super().upsert(db, item, match_keys)

    def read(self, db: DBSession, item: ToponymGet) -> ToponymGet:
        return super().read(db, item)

    def read_all(self, db: DBSession, **filter) -> list[ToponymGet]:
        return super().read_all(db, **filter)

    def update(self, db: DBSession, item: ToponymUpdate) -> ToponymGet:
        return super().update(db, item)

    def delete(self, db: DBSession, item: ToponymGet) -> ToponymGet:
        return super().delete(db, item)
