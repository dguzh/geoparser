import typing as t

from pydantic_core import PydanticCustomError
from sqlmodel import Session as DBSession
from sqlmodel import select

from geoparser.annotator.db.crud.base import BaseRepository
from geoparser.annotator.db.crud.toponym import ToponymRepository
from geoparser.annotator.db.models.document import (
    Document,
    DocumentCreate,
    DocumentGet,
    DocumentUpdate,
)


class DocumentRepository(BaseRepository):
    model = Document

    @classmethod
    def get_highest_index(cls, db: DBSession, session_id: str):
        return db.exec(
            select(Document.doc_index)
            .where(Document.session_id == session_id)
            .order_by(Document.doc_index.desc())
        ).scalar()

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
    def create(cls, db: DBSession, item: DocumentCreate) -> DocumentGet:
        # Create the main document object
        if item.doc_index:
            cls.validate_doc_index(db, item)
        else:
            item.doc_index = cls.get_highest_index(db, item.session.id) + 1
        document = super().create(db, item)
        # Create toponyms if provided
        if item.toponyms:
            for toponym in item.toponyms:
                toponym.document_id = document.id
                ToponymRepository.create(db, toponym)
        return document

    @classmethod
    def upsert(
        cls,
        db: DBSession,
        item: t.Union[DocumentCreate, DocumentUpdate],
        match_keys: t.List[str] = ["id"],
    ) -> DocumentGet:
        filter_args = [
            getattr(cls.model, key) == getattr(item, key) for key in match_keys
        ]
        existing_item = db.exec(select(cls.model).where(*filter_args)).first()
        if existing_item and item.doc_index:
            cls.validate_doc_index(db, item)
        else:
            item.doc_index = cls.get_highest_index(db, item.session.id) + 1
        return super().upsert(db, item, match_keys)

    @classmethod
    def read(cls, db: DBSession, id: str) -> DocumentGet:
        return super().read(db, id)

    @classmethod
    def read_all(cls, db: DBSession, **filters) -> list[DocumentGet]:
        return super().read_all(db, **filters)

    @classmethod
    def update(cls, db: DBSession, item: DocumentUpdate) -> DocumentGet:
        if item.doc_index:
            cls.validate_doc_index(db, item)
        return super().update(db, item)

    @classmethod
    def delete(cls, db: DBSession, id: str) -> DocumentGet:
        deleted = super().delete(db, id)
        cls.reindex_documents(db, id)
        return deleted
