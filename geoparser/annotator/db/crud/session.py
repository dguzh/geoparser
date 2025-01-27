import json
import typing as t

from sqlmodel import Session as DBSession

from geoparser.annotator.db.crud.base import BaseRepository
from geoparser.annotator.db.crud.document import DocumentRepository
from geoparser.annotator.db.crud.settings import SessionSettingsRepository
from geoparser.annotator.db.models.document import DocumentCreate
from geoparser.annotator.db.models.session import (
    Session,
    SessionCreate,
    SessionGet,
    SessionUpdate,
)
from geoparser.annotator.db.models.settings import SessionSettingsCreate
from geoparser.annotator.db.models.toponym import ToponymCreate


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

    def create_from_json(self, db: DBSession, json_str: str) -> SessionGet:
        content = json.loads(json_str)
        session = SessionCreate.model_validate(
            {
                **{
                    key: content[key]
                    for key in ["id", "created_at", "last_updated", "gazetteer"]
                },
                "settings": SessionSettingsCreate.model_validate(content["settings"]),
                "documents": [
                    DocumentCreate.model_validate(
                        {
                            **document_dict,
                            "toponyms": [
                                ToponymCreate.model_validate(toponym_dict)
                                for toponym_dict in document_dict["toponyms"]
                            ],
                        }
                    )
                    for document_dict in content["documents"]
                ],
            }
        )
        return self.create(db, session)

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
