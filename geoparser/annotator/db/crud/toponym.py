import typing as t

from pydantic_core import PydanticCustomError
from sqlmodel import Session as DBSession
from sqlmodel import select

from geoparser.annotator.db.crud.base import BaseRepository
from geoparser.annotator.db.models.toponym import Toponym, ToponymCreate, ToponymUpdate


class ToponymRepository(BaseRepository):
    model = Toponym

    @classmethod
    def validate_overlap(
        cls, db: DBSession, toponym: ToponymCreate, document_id: str
    ) -> bool:
        overlapping = db.exec(
            select(Toponym)
            .where(Toponym.document_id == document_id)
            .where((Toponym.start <= toponym.end) & (Toponym.end >= toponym.start))
        ).all()
        if overlapping:
            raise PydanticCustomError(
                "overlapping_toponyms",
                f"Toponyms overlap: {overlapping}",
            )
        return True

    @classmethod
    def create(
        cls,
        db: DBSession,
        item: ToponymCreate,
        exclude: t.Optional[list[str]] = [],
        additional: t.Optional[dict[str, t.Any]] = {},
    ) -> Toponym:
        assert (
            "document_id" in additional
        ), "toponym cannot be created without link to document"
        cls.validate_overlap(db, item, additional["document_id"])
        return super().create(db, item, exclude=exclude, additional=additional)

    @classmethod
    def read(cls, db: DBSession, id: str) -> Toponym:
        return super().read(db, id)

    @classmethod
    def read_all(cls, db: DBSession, **filters) -> list[Toponym]:
        return super().read_all(db, **filters)

    @classmethod
    def update(cls, db: DBSession, item: ToponymUpdate) -> Toponym:
        cls.validate_overlap(db, item)
        return super().update(db, item)

    @classmethod
    def delete(cls, db: DBSession, id: str) -> Toponym:
        return super().delete(db, id)
