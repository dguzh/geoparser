import typing as t

from sqlmodel import Session as DBSession

from geoparser.annotator.db.crud import DocumentRepository, SessionSettingsRepository
from geoparser.annotator.db.crud.base import BaseRepository
from geoparser.annotator.db.models.session import (
    Session,
    SessionCreate,
    SessionGet,
    SessionUpdate,
)


class SessionRepository(BaseRepository):
    def __init__(self):
        self.model = Session

    def create(self, db: DBSession, item: SessionCreate) -> SessionGet:
        # create the main session object
        session = super().create(db, item)
        # create settings if provided
        if item.settings:
            item.settings.session_id = session.id
            SessionSettingsRepository().create(db, item.settings)
        # create documents if provided
        if item.documents:
            for document in item.documents:
                document.session_id = session.id
                DocumentRepository().create(db, document)
        return session

    def upsert(
        self,
        db: DBSession,
        item: t.Union[SessionCreate, SessionUpdate],
        match_keys: t.List[str] = ["id"],
    ) -> SessionGet:
        return super().upsert(db, item, match_keys)

    def read(self, db: DBSession, item: SessionGet) -> SessionGet:
        return super().read(db, item)

    def read_all(self, db: DBSession, **filters) -> list[SessionGet]:
        return super().read_all(db, **filters)

    def update(self, db: DBSession, item: SessionUpdate) -> SessionGet:
        return super().update(db, item)

    def delete(self, db: DBSession, item: SessionGet) -> SessionGet:
        return super().delete(db, item)
