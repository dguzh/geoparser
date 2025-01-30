import json
import typing as t
import uuid

from fastapi import UploadFile
from fastapi.encoders import jsonable_encoder
from sqlmodel import Session as DBSession
from werkzeug.utils import secure_filename

from geoparser import Geoparser
from geoparser.annotator.db.crud.base import BaseRepository
from geoparser.annotator.db.crud.document import DocumentRepository
from geoparser.annotator.db.crud.settings import SessionSettingsRepository
from geoparser.annotator.db.models.document import DocumentCreate
from geoparser.annotator.db.models.session import Session, SessionCreate, SessionUpdate
from geoparser.annotator.db.models.settings import SessionSettingsCreate
from geoparser.annotator.db.models.toponym import ToponymCreate


class SessionRepository(BaseRepository):
    model = Session

    @classmethod
    def create(
        cls,
        db: DBSession,
        item: SessionCreate,
        exclude: t.Optional[list[str]] = [],
        additional: t.Optional[dict[str, t.Any]] = {},
    ) -> Session:
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
        return session

    @classmethod
    def create_from_json(cls, db: DBSession, json_str: str) -> Session:
        # Parse the JSON input
        content = json.loads(json_str)
        session = SessionCreate.model_validate(
            {
                **content,
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
    def create_from_text_files(
        cls,
        db: DBSession,
        geoparser: Geoparser,
        files: list[UploadFile],
        gazetteer: str,
        spacy_model: str,
        apply_spacy: bool = False,
    ):
        if apply_spacy:
            geoparser.nlp = geoparser.setup_spacy(spacy_model)
        documents = []
        for file in files:
            toponyms = []
            filename = secure_filename(file.filename)
            text = file.file.read().decode("utf-8")
            if apply_spacy:
                doc = geoparser.nlp(text)
                toponyms = [
                    ToponymCreate(text=top.text, start=top.start_char, end=top.end_char)
                    for top in doc.toponyms
                ]
            documents.append(
                DocumentCreate(
                    filename=filename,
                    spacy_model=spacy_model,
                    text=text,
                    toponyms=toponyms,
                    spacy_applied=apply_spacy,
                )
            )
        return cls.create(db, SessionCreate(gazetteer=gazetteer, documents=documents))

    @classmethod
    def read(cls, db: DBSession, id: str) -> Session:
        return super().read(db, id)

    @classmethod
    def read_to_json(cls, db: DBSession, id: str) -> dict:
        item = cls.read(db, id)
        result = SessionCreate(
            **item.model_dump(),
            settings=item.settings,
            documents=[
                DocumentCreate(**document.model_dump(), toponyms=document.toponyms)
                for document in item.documents
            ]
        )
        return jsonable_encoder(result)

    @classmethod
    def read_all(cls, db: DBSession, **filters) -> list[Session]:
        return super().read_all(db, **filters)

    @classmethod
    def update(cls, db: DBSession, item: SessionUpdate) -> Session:
        return super().update(db, item)

    @classmethod
    def delete(cls, db: DBSession, id: str) -> Session:
        return super().delete(db, id)
