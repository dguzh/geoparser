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
    def __init__(self):
        self.model = Document

    def get_highest_index(self, db: DBSession, session_id: str):
        return db.exec(
            select(Document.doc_index)
            .where(Document.session_id == session_id)
            .order_by(Document.doc_index.desc())
        ).scalar()

    def reindex_documents(self, db: DBSession, session_id: str):
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

    def validate_doc_index(self, db: DBSession, document: DocumentGet):
        highest_index = self.get_highest_index(db, document.session.id)
        if document.doc_index <= highest_index:
            raise PydanticCustomError(
                "existing_doc_index",
                "there is already a document with doc_index {doc_index}. use doc_index {free_index} instead (next free index)",
                {"doc_index": document.doc_index, "free_index": highest_index + 1},
            )
        return True

    def create(self, db: DBSession, item: DocumentCreate) -> DocumentGet:
        # create the main document object
        if item.doc_index:
            self.validate_doc_index(db, item)
        else:
            item.doc_index = self.get_highest_index(db, item.session.id) + 1
        document = super().create(db, item)
        # create toponyms if provided
        if item.toponyms:
            for toponym in item.documents:
                toponym.document_id = toponym.id
                ToponymRepository().create(db, toponym)
        return document

    def upsert(
        self,
        db: DBSession,
        item: t.Union[DocumentCreate, DocumentUpdate],
        match_keys: t.List[str] = ["id"],
    ) -> DocumentGet:
        filter_args = [
            getattr(self.model, key) == getattr(item, key) for key in match_keys
        ]
        existing_item = db.exec(select(self.model).where(*filter_args)).first()
        if existing_item and item.doc_index:
            self.validate_doc_index(db, item)
        else:
            item.doc_index = self.get_highest_index(db, item.session.id) + 1
        return super().upsert(db, item, match_keys)

    def read(self, db: DBSession, item: DocumentGet) -> DocumentGet:
        return super().read(db, item)

    def read_all(self, db: DBSession, **filter) -> list[DocumentGet]:
        return super().read_all(db, **filter)

    def update(self, db: DBSession, item: DocumentUpdate) -> DocumentGet:
        if item.doc_index:
            self.validate_doc_index(db, item)
        return super().update(db, item)

    def delete(self, db: DBSession, item: DocumentGet) -> DocumentGet:
        deleted = super().delete(db, item)
        self.reindex_documents(db, item)
        return deleted
