import typing as t

from markupsafe import Markup
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
    def get_pre_annotated_text(cls, db: DBSession, id: str) -> str:
        document = cls.read(db, id)
        html_parts = []
        last_idx = 0
        for toponym in document.toponyms:
            start_char = toponym.start
            end_char = toponym.end
            annotated = toponym.loc_id != ""
            # Escape the text before the toponym
            before_toponym = Markup.escape(document.text[last_idx:start_char])
            html_parts.append(before_toponym)

            # Create the span for the toponym
            toponym_text = Markup.escape(document.text[start_char:end_char])
            span = Markup(
                '<span class="toponym {annotated_class}" data-start="{start}" data-end="{end}">{text}</span>'
            ).format(
                annotated_class="annotated" if annotated else "",
                start=start_char,
                end=end_char,
                text=toponym_text,
            )
            html_parts.append(span)
            last_idx = end_char
        # Append the remaining text after the last toponym
        after_toponym = Markup.escape(document.text[last_idx:])
        html_parts.append(after_toponym)
        # Combine all parts into a single Markup object
        html = Markup("").join(html_parts)
        return html

    @classmethod
    def get_progress(cls, db: DBSession, **filters) -> t.Iterator[dict]:
        documents = cls.read_all(db, **filters)
        for document in documents:
            total_toponyms = len(document.toponyms)
            annotated_toponyms = sum(t.loc_id != "" for t in document.toponyms)
            progress_percentage = (
                (annotated_toponyms / total_toponyms) * 100 if total_toponyms > 0 else 0
            )
            yield {
                "filename": document.filename,
                "doc_index": document.doc_index,
                "annotated_toponyms": annotated_toponyms,
                "total_toponyms": total_toponyms,
                "progress_percentage": progress_percentage,
            }

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
