from pydantic_core import PydanticCustomError
from sqlmodel import Session as DBSession

from geoparser.annotator.db.crud.base import BaseRepository
from geoparser.annotator.db.models.toponym import (
    Toponym,
    ToponymCreate,
    ToponymGet,
    ToponymUpdate,
)


class ToponymRepository(BaseRepository):
    def __init__(self):
        model = Toponym

    def validate_overlap(self, db: DBSession, toponym: ToponymCreate) -> bool:
        toponyms = sorted(
            self.read_all(db, Toponym.document.id == toponym.document.id) + [toponym],
            key=lambda x: x.start,
        )
        toponym_bigrams = [
            (toponyms[i], toponyms[i + 1]) for i in range(len(toponyms) - 1)
        ]
        for first, second in toponym_bigrams:
            if first.end >= second.start:
                raise PydanticCustomError(
                    "overlapping_toponyms",
                    "toponyms (start={start1}, end={end1}, text={text1}) and (start={start2}, end={end2}, text={text2}) are overlapping",
                    {
                        "start1": first.start,
                        "end1": first.end,
                        "text1": first.text,
                        "start2": second.start,
                        "end2": second.end,
                        "text2": second.text,
                    },
                )
        return True

    def create(self, db: DBSession, item: ToponymCreate) -> ToponymGet:
        self.validate_overlap(item)
        return super().create(db, item)

    def read(self, db: DBSession, item: ToponymGet) -> ToponymGet:
        return super().read(db, item)

    def read_all(self, db: DBSession, filter: dict) -> list[ToponymGet]:
        return super().read_all(db, filter)

    def update(self, db: DBSession, item: ToponymUpdate) -> ToponymGet:
        return super().update(db, item)

    def delete(self, db: DBSession, item: ToponymGet) -> ToponymGet:
        return super().delete(db, item)
