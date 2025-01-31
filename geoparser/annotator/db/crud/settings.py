import typing as t
import uuid

from sqlmodel import Session as DBSession

from geoparser.annotator.db.crud.base import BaseRepository
from geoparser.annotator.db.models.settings import (
    SessionSettings,
    SessionSettingsCreate,
    SessionSettingsUpdate,
)
from geoparser.annotator.exceptions import SessionSettingsNotFoundException


class SessionSettingsRepository(BaseRepository):
    model = SessionSettings
    exception_factory: t.Callable[[str, uuid.UUID], Exception] = (
        lambda x, y: SessionSettingsNotFoundException(f"{x} with ID {y} not found.")
    )

    @classmethod
    def create(
        cls,
        db: DBSession,
        item: SessionSettingsCreate,
        exclude: t.Optional[list[str]] = [],
        additional: t.Optional[dict[str, t.Any]] = {},
    ) -> SessionSettings:
        assert (
            "session_id" in additional
        ), "settings cannot be created without link to session"
        return super().create(db, item, exclude=exclude, additional=additional)

    @classmethod
    def read(cls, db: DBSession, id: uuid.UUID) -> SessionSettings:
        return super().read(db, id)

    @classmethod
    def read_all(cls, db: DBSession, **filters) -> list[SessionSettings]:
        return super().read_all(db, **filters)

    @classmethod
    def update(cls, db: DBSession, item: SessionSettingsUpdate) -> SessionSettings:
        return super().update(db, item)

    @classmethod
    def delete(cls, db: DBSession, id: uuid.UUID) -> SessionSettings:
        return super().delete(db, id)
