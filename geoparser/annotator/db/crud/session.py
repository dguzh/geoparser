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
    model = Session

    @classmethod
    def create(cls, db: DBSession, item: SessionCreate) -> SessionGet:
        # Create the main session object
        session = super().create(db, item)
        # Create settings if provided
        if item.settings:
            item.settings.session_id = session.id
            SessionSettingsRepository.create(db, item.settings)
        # Create documents if provided
        if item.documents:
            for document in item.documents:
                document.session_id = session.id
                DocumentRepository.create(db, document)
        return session

    @classmethod
    def create_from_json(cls, db: DBSession, json_str: str) -> SessionGet:
        # Parse the JSON input
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
        return cls.create(db, session)

    @classmethod
    def upsert(
        cls,
        db: DBSession,
        item: t.Union[SessionCreate, SessionUpdate],
        match_keys: t.List[str] = ["id"],
    ) -> SessionGet:
        return super().upsert(db, item, match_keys)

    @classmethod
    def read(cls, db: DBSession, id: str) -> SessionGet:
        return super().read(db, id)

    @classmethod
    def read_all(cls, db: DBSession, **filters) -> list[SessionGet]:
        return super().read_all(db, **filters)

    @classmethod
    def update(cls, db: DBSession, item: SessionUpdate) -> SessionGet:
        return super().update(db, item)

    @classmethod
    def delete(cls, db: DBSession, id: str) -> SessionGet:
        return super().delete(db, id)
