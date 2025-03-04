import typing as t
import uuid

from sqlmodel import Session as DBSession
from sqlmodel import select

from geoparser.db.crud.base import BaseRepository
from geoparser.db.models.run import Run, RunCreate, RunUpdate


class RunRepository(BaseRepository):
    model = Run
    exception_factory: t.Callable = lambda x, y: ValueError(
        f"Run with ID {y} not found."
    )

    @classmethod
    def create(
        cls,
        db: DBSession,
        item: RunCreate,
        exclude: t.Optional[list[str]] = [],
        additional: t.Optional[dict[str, t.Any]] = {},
    ) -> Run:
        return super().create(db, item, exclude, additional)

    @classmethod
    def read(cls, db: DBSession, id: uuid.UUID) -> Run:
        return super().read(db, id)

    @classmethod
    def read_all_by_session(cls, db: DBSession, session_id: uuid.UUID) -> list[Run]:
        """Get all runs for a specific session"""
        statement = select(cls.model).where(cls.model.session_id == session_id)
        return db.exec(statement).all()

    @classmethod
    def update(cls, db: DBSession, item: RunUpdate) -> Run:
        return super().update(db, item)

    @classmethod
    def delete(cls, db: DBSession, id: uuid.UUID) -> Run:
        return super().delete(db, id)

    @classmethod
    def mark_completed(
        cls, db: DBSession, id: uuid.UUID, metadata: t.Optional[str] = None
    ) -> Run:
        """Mark a run as completed with an optional metadata string"""
        from datetime import datetime

        run_update = RunUpdate(
            id=id,
            completed_at=datetime.now(),
            status="completed",
            metadata=metadata,
        )
        return cls.update(db, run_update)

    @classmethod
    def mark_failed(cls, db: DBSession, id: uuid.UUID, error_message: str) -> Run:
        """Mark a run as failed with an error message"""
        from datetime import datetime

        run_update = RunUpdate(
            id=id,
            completed_at=datetime.now(),
            status="failed",
            metadata=error_message,
        )
        return cls.update(db, run_update)
