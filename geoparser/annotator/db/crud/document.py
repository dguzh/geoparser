import typing as t

from pydantic_core import PydanticCustomError
from sqlmodel import Session as DBSession
from sqlmodel import select

from geoparser.annotator.db.crud.base import BaseRepository
from geoparser.annotator.db.crud.toponym import ToponymRepository
from geoparser.annotator.db.models.document import (
    Document,
    DocumentCreate,
    DocumentUpdate,
)


class DocumentRepository(BaseRepository):
    model = Document

    @classmethod
    def get_highest_index(cls, db: DBSession, session_id: str):
        result = db.exec(
            select(Document.doc_index)
            .where(Document.session_id == session_id)
            .order_by(Document.doc_index.desc())
        ).first()
        return result if result is not None else -1

    @classmethod
    def reindex_documents(cls, db: DBSession, session_id: str):
        documents = db.exec(
            select(Document)
            .where(Document.session_id == session_id)
            .order_by(Document.doc_index.asc())
        ).all()
        for i, doc in enumerate(documents):
            if doc.doc_index != i:
                doc.doc_index = i
                db.add(doc)
        db.commit()

    @classmethod
    def validate_doc_index(cls, db: DBSession, document: DocumentCreate):
        highest_index = cls.get_highest_index(db, document.session.id)
        if document.doc_index <= highest_index:
            raise PydanticCustomError(
                "existing_doc_index",
                "there is already a document with doc_index {doc_index}. use doc_index {free_index} instead (next free index)",
                {"doc_index": document.doc_index, "free_index": highest_index + 1},
            )
        return True

    @classmethod
    def create(
        cls,
        db: DBSession,
        item: DocumentCreate,
        exclude: t.Optional[list[str]] = [],
        additional: t.Optional[dict[str, t.Any]] = {},
    ) -> Document:
        assert (
            "session_id" in additional
        ), "document cannot be created without link to session"
        # Create the main document object
        document = super().create(
            db,
            item,
            exclude=["toponyms", *exclude],
            additional={
                "doc_index": cls.get_highest_index(db, additional["session_id"]) + 1,
                **additional,
            },
        )
        # Create toponyms if provided
        if item.toponyms:
            for toponym in item.toponyms:
                ToponymRepository.create(
                    db, toponym, additional={"document_id": document.id}
                )
        return document

    @classmethod
    def read(cls, db: DBSession, id: str) -> Document:
        return super().read(db, id)

    @classmethod
    def read_all(cls, db: DBSession, **filters) -> list[Document]:
        return super().read_all(db, **filters)

    @classmethod
    def update(cls, db: DBSession, item: DocumentUpdate) -> Document:
        if item.doc_index:
            cls.validate_doc_index(db, item)
        return super().update(db, item)

    @classmethod
    def delete(cls, db: DBSession, id: str) -> Document:
        deleted = super().delete(db, id)
        cls.reindex_documents(db, id)
        return deleted
