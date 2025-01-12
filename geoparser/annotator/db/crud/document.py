from pydantic_core import PydanticCustomError
from sqlmodel import Session as DBSession
from sqlmodel import select

from geoparser.annotator.db.crud.base import BaseRepository
from geoparser.annotator.db.models.document import (
    Document,
    DocumentCreate,
    DocumentGet,
    DocumentUpdate,
)


class DocumentRepository(BaseRepository):
    def __init__(self):
        model = Document

    def reindex_documents(self, db: DBSession, document: DocumentGet):
        sorted_documents = sorted(
            self.read_all(db, Document.session.id == document.session.id),
            key=lambda x: x.doc_index,
        )
        for i, doc in enumerate(sorted_documents):
            if i != doc.doc_index:
                doc.doc_index = i
                self.update(db, doc)

    def get_hightest_index(self, db: DBSession, session_id: str):
        return db.exec(
            select(Document.doc_index)
            .where(Document.session.id == session_id)
            .order_by(Document.doc_index.desc())
        ).first()

    def validate_doc_index(self, db: DBSession, document: DocumentGet):
        highest_index = self.get_hightest_index(db, document.session.id)
        if document.doc_index <= highest_index:
            raise PydanticCustomError(
                "existing_doc_index",
                "there is already a document with doc_index {doc_index}. use doc_index {free_index} instead (next free index)",
                {"doc_index": document.doc_index, "free_index": highest_index + 1},
            )
        return True

    def create(self, db: DBSession, item: DocumentCreate) -> DocumentGet:
        if item.doc_index:
            self.validate_doc_index(db, item)
        else:
            item.doc_index = self.get_hightest_index(db, item.session.id) + 1
        return super().create(db, item)

    def read(self, db: DBSession, item: DocumentGet) -> DocumentGet:
        return super().read(db, item)

    def read_all(self, db: DBSession, filter: dict) -> list[DocumentGet]:
        return super().read_all(db, filter)

    def update(self, db: DBSession, item: DocumentUpdate) -> DocumentGet:
        return super().update(db, item)

    def delete(self, db: DBSession, item: DocumentGet) -> DocumentGet:
        deleted = super().delete(db, item)
        self.reindex_documents(db, item)
        return deleted
