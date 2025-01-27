import typing as t

from sqlmodel import Session as DBSession

from geoparser.annotator.db.crud.base import BaseRepository
from geoparser.annotator.db.models.settings import (
    SessionSettings,
    SessionSettingsCreate,
    SessionSettingsGet,
    SessionSettingsUpdate,
)


class SessionSettingsRepository(BaseRepository):
    model = SessionSettings

    @classmethod
    def create(cls, db: DBSession, item: SessionSettingsCreate) -> SessionSettingsGet:
        return super().create(db, item)

    @classmethod
    def upsert(
        cls,
        db: DBSession,
        item: t.Union[SessionSettingsCreate, SessionSettingsUpdate],
        match_keys: t.List[str] = ["id"],
    ) -> SessionSettingsGet:
        return super().upsert(db, item, match_keys)

    @classmethod
    def read(cls, db: DBSession, id: str) -> SessionSettingsGet:
        return super().read(db, id)

    @classmethod
    def read_all(cls, db: DBSession, **filters) -> list[SessionSettingsGet]:
        return super().read_all(db, **filters)

    @classmethod
    def update(cls, db: DBSession, item: SessionSettingsUpdate) -> SessionSettingsGet:
        return super().update(db, item)

    @classmethod
    def delete(cls, db: DBSession, id: str) -> SessionSettingsGet:
        return super().delete(db, id)
