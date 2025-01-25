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
    def __init__(self):
        self.model = SessionSettings

    def create(self, db: DBSession, item: SessionSettingsCreate) -> SessionSettingsGet:
        return super().create(db, item)

    def upsert(
        self,
        db: DBSession,
        item: t.Union[SessionSettingsCreate, SessionSettingsUpdate],
        match_keys: t.List[str] = ["id"],
    ) -> SessionSettingsGet:
        return super().upsert(db, item, match_keys)

    def read(self, db: DBSession, item: SessionSettingsGet) -> SessionSettingsGet:
        return super().read(db, item)

    def read_all(self, db: DBSession, **filters) -> list[SessionSettingsGet]:
        return super().read_all(db, **filters)

    def update(self, db: DBSession, item: SessionSettingsUpdate) -> SessionSettingsGet:
        return super().update(db, item)

    def delete(self, db: DBSession, item: SessionSettingsGet) -> SessionSettingsGet:
        return super().delete(db, item)
