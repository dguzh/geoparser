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
    model = Toponym

    @classmethod
    def validate_overlap(cls, db: DBSession, toponym: ToponymCreate) -> bool:
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

    @classmethod
    def create(cls, db: DBSession, item: ToponymCreate) -> ToponymGet:
        cls.validate_overlap(db, item)
        return super().create(db, item)

    @classmethod
    def upsert(
        cls,
        db: DBSession,
        item: t.Union[ToponymCreate, ToponymUpdate],
        match_keys: t.List[str] = ["id"],
    ) -> ToponymGet:
        cls.validate_overlap(db, item)
        return super().upsert(db, item, match_keys)

    @classmethod
    def read(cls, db: DBSession, id: str) -> ToponymGet:
        return super().read(db, id)

    @classmethod
    def read_all(cls, db: DBSession, **filters) -> list[ToponymGet]:
        return super().read_all(db, **filters)

    @classmethod
    def update(cls, db: DBSession, item: ToponymUpdate) -> ToponymGet:
        cls.validate_overlap(db, item)
        return super().update(db, item)

    @classmethod
    def delete(cls, db: DBSession, id: str) -> ToponymGet:
        return super().delete(db, id)
