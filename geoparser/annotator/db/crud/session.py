import json
import typing as t
import uuid

from fastapi.encoders import jsonable_encoder
from sqlmodel import Session as DBSession

from geoparser.annotator.db.crud.base import BaseRepository
from geoparser.annotator.db.crud.document import DocumentRepository
from geoparser.annotator.db.crud.settings import SessionSettingsRepository
from geoparser.annotator.db.models.document import AnnotatorDocumentCreate
from geoparser.annotator.db.models.session import (
    AnnotatorSession,
    AnnotatorSessionCreate,
    AnnotatorSessionDownload,
    AnnotatorSessionUpdate,
)
from geoparser.annotator.db.models.toponym import AnnotatorToponymCreate
from geoparser.annotator.exceptions import SessionNotFoundException


class SessionRepository(BaseRepository):
    model = AnnotatorSession
    exception_factory: t.Callable = lambda x, y: SessionNotFoundException(
        f"{x} with ID {y} not found."
    )

    @classmethod
    def create(
        cls,
        db: DBSession,
        item: AnnotatorSessionCreate,
        exclude: t.Optional[list[str]] = [],
        additional: t.Optional[dict[str, t.Any]] = {},
    ) -> AnnotatorSession:
        # Create the main session object
        session = super().create(
            db, item, exclude=["settings", "documents", *exclude], additional=additional
        )
        # Create settings if provided
        if item.settings:
            SessionSettingsRepository.create(
                db, item.settings, additional={"session_id": session.id}
            )
        # Create documents if provided
        if item.documents:
            for document in item.documents:
                DocumentRepository.create(
                    db, document, additional={"session_id": session.id}
                )
        # session object expired when creating settings and documents so we refresh it
        db.refresh(session)
        return session

    @classmethod
    def create_from_json(
        cls, db: DBSession, json_str: str, keep_id: bool = False
    ) -> AnnotatorSession:
        # Parse the JSON input
        content = json.loads(json_str)
        session = AnnotatorSessionCreate.model_validate(
            {
                **content,
                "documents": [
                    AnnotatorDocumentCreate.model_validate(
                        {
                            **document_dict,
                            "toponyms": [
                                AnnotatorToponymCreate.model_validate(toponym_dict)
                                for toponym_dict in document_dict["toponyms"]
                            ],
                            "spacy_applied": True,
                        }
                    )
                    for document_dict in content["documents"]
                ],
            }
        )
        additional = {}
        if keep_id and (session_id := content.get("session_id")):
            additional["id"] = uuid.UUID(session_id)
        return cls.create(db, session, additional=additional)

    @classmethod
    def read(cls, db: DBSession, id: uuid.UUID) -> AnnotatorSession:
        return super().read(db, id)

    @classmethod
    def read_to_json(cls, db: DBSession, id: uuid.UUID) -> dict:
        item = cls.read(db, id)
        result = AnnotatorSessionDownload(
            **item.model_dump(),
            documents=[
                AnnotatorDocumentCreate(
                    **document.model_dump(), toponyms=document.toponyms
                )
                for document in item.documents
            ],
        )
        return jsonable_encoder(result)

    @classmethod
    def read_all(cls, db: DBSession, **filters) -> list[AnnotatorSession]:
        return super().read_all(db, **filters)

    @classmethod
    def update(cls, db: DBSession, item: AnnotatorSessionUpdate) -> AnnotatorSession:
        return super().update(db, item)

    @classmethod
    def delete(cls, db: DBSession, id: uuid.UUID) -> AnnotatorSession:
        return super().delete(db, id)
