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
        model = SessionSettings

    def create(self, db: DBSession, item: SessionSettingsCreate) -> SessionSettingsGet:
        return super().create(db, item)

    def read(self, db: DBSession, item: SessionSettingsGet) -> SessionSettingsGet:
        return super().read(db, item)

    def read_all(self, db: DBSession, filter: dict) -> list[SessionSettingsGet]:
        return super().read_all(db, filter)

    def update(self, db: DBSession, item: SessionSettingsUpdate) -> SessionSettingsGet:
        return super().update(db, item)

    def delete(self, db: DBSession, item: SessionSettingsGet) -> SessionSettingsGet:
        return super().delete(db, item)
