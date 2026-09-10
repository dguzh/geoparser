import typing as t
import uuid

from sqlmodel import Session as DBSession

from geoparser.annotator.db.crud.base import BaseRepository
from geoparser.annotator.db.models.settings import (
    AnnotatorSessionSettings,
    AnnotatorSessionSettingsCreate,
    AnnotatorSessionSettingsUpdate,
)
from geoparser.annotator.exceptions import SessionSettingsNotFoundException


class SessionSettingsRepository(BaseRepository[AnnotatorSessionSettings]):
    model = AnnotatorSessionSettings
    exception_factory: t.Callable[[str, uuid.UUID], Exception] = lambda x, y: (
        SessionSettingsNotFoundException(f"{x} with ID {y} not found.")
    )

    @classmethod
    # BaseRepository declares the widest input type (SQLModel); each repository
    # deliberately accepts its own Create/Update model. Callers always go
    # through the concrete repository, so the precise signature is worth more
    # here than strict substitutability.
    def create(  # ty: ignore[invalid-method-override]
        cls,
        db: DBSession,
        item: AnnotatorSessionSettingsCreate,
        exclude: list[str] | None = None,
        additional: dict[str, t.Any] | None = None,
    ) -> AnnotatorSessionSettings:
        assert additional and "session_id" in additional, (
            "settings cannot be created without link to session"
        )
        return super().create(db, item, exclude=exclude, additional=additional)

    @classmethod
    def read(cls, db: DBSession, id: uuid.UUID) -> AnnotatorSessionSettings:
        return super().read(db, id)

    @classmethod
    def read_all(cls, db: DBSession, **filters) -> list[AnnotatorSessionSettings]:
        return super().read_all(db, **filters)

    @classmethod
    def update(  # ty: ignore[invalid-method-override]
        cls, db: DBSession, item: AnnotatorSessionSettingsUpdate
    ) -> AnnotatorSessionSettings:
        return super().update(db, item)

    @classmethod
    def delete(cls, db: DBSession, id: uuid.UUID) -> AnnotatorSessionSettings:
        return super().delete(db, id)
