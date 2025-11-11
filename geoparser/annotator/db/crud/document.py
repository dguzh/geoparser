import typing as t
import uuid

from fastapi import UploadFile
from markupsafe import Markup
from sqlmodel import Session as DBSession
from sqlmodel import select
from werkzeug.utils import secure_filename

from geoparser.annotator.db.crud.base import BaseRepository
from geoparser.annotator.db.crud.toponym import ToponymRepository
from geoparser.annotator.db.models.document import (
    AnnotatorDocument,
    AnnotatorDocumentCreate,
    AnnotatorDocumentUpdate,
)
from geoparser.annotator.db.models.toponym import AnnotatorToponymCreate
from geoparser.annotator.exceptions import DocumentNotFoundException
from geoparser.modules.recognizers.spacy import SpacyRecognizer


class DocumentRepository(BaseRepository):
    model = AnnotatorDocument
    exception_factory: t.Callable[[str, uuid.UUID], Exception] = (
        lambda x, y: DocumentNotFoundException(f"{x} with ID {y} not found.")
    )

    @classmethod
    def get_highest_index(cls, db: DBSession, session_id: uuid.UUID) -> int:
        result = db.exec(
            select(AnnotatorDocument.doc_index)
            .where(AnnotatorDocument.session_id == session_id)
            .order_by(AnnotatorDocument.doc_index.desc())
        ).first()
        return result if result is not None else -1

    @classmethod
    def _reindex_documents(cls, db: DBSession, session_id: uuid.UUID):
        documents = db.exec(
            select(AnnotatorDocument)
            .where(AnnotatorDocument.session_id == session_id)
            .order_by(AnnotatorDocument.doc_index.asc())
        ).all()
        for i, doc in enumerate(documents):
            if doc.doc_index != i:
                doc.doc_index = i
                db.add(doc)
        db.commit()

    @classmethod
    def create(
        cls,
        db: DBSession,
        item: AnnotatorDocumentCreate,
        exclude: t.Optional[list[str]] = [],
        additional: t.Optional[dict[str, t.Any]] = {},
    ) -> AnnotatorDocument:
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
    def create_from_text_files(
        cls,
        db: DBSession,
        files: list[UploadFile],
        session_id: uuid.UUID,
        spacy_model: str,
        apply_spacy: bool = False,
    ) -> list[AnnotatorDocument]:
        recognizer = None
        if apply_spacy:
            recognizer = SpacyRecognizer(model_name=spacy_model)

        documents = []
        for file in files:
            toponyms = []
            filename = secure_filename(file.filename)
            text = file.file.read().decode("utf-8")
            if apply_spacy and recognizer:
                references = recognizer.predict_references([text])[0]
                toponyms = [
                    AnnotatorToponymCreate(text=text[start:end], start=start, end=end)
                    for start, end in references
                ]
            document = cls.create(
                db,
                AnnotatorDocumentCreate(
                    filename=filename,
                    spacy_model=spacy_model,
                    text=text,
                    toponyms=toponyms,
                    spacy_applied=apply_spacy,
                ),
                additional={"session_id": session_id},
            )
            documents.append(document)
        return documents

    @classmethod
    def read(cls, db: DBSession, id: uuid.UUID) -> AnnotatorDocument:
        return super().read(db, id)

    @classmethod
    def get_pre_annotated_text(cls, db: DBSession, id: uuid.UUID) -> str:
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
                "doc_id": document.id,
                "annotated_toponyms": annotated_toponyms,
                "total_toponyms": total_toponyms,
                "progress_percentage": progress_percentage,
            }

    @classmethod
    def get_document_progress(cls, db: DBSession, id: uuid.UUID) -> dict[str, t.Any]:
        return next(cls.get_progress(db, id=id))

    @classmethod
    def read_all(cls, db: DBSession, **filters) -> list[AnnotatorDocument]:
        return super().read_all(db, **filters)

    @classmethod
    def update(cls, db: DBSession, item: AnnotatorDocumentUpdate) -> AnnotatorDocument:
        return super().update(db, item)

    @classmethod
    def parse(cls, db: DBSession, id: uuid.UUID) -> AnnotatorDocument:
        document = cls.read(db, id)
        recognizer = SpacyRecognizer(model_name=document.spacy_model)
        references = recognizer.predict_references([document.text])[0]
        spacy_toponyms = [
            AnnotatorToponymCreate(text=document.text[start:end], start=start, end=end)
            for start, end in references
        ]
        old_toponyms = document.toponyms
        new_toponyms = ToponymRepository._remove_duplicates(
            old_toponyms, spacy_toponyms
        )
        for toponym in new_toponyms:
            ToponymRepository.create(
                db, toponym, additional={"document_id": document.id}
            )
        document = cls.update(
            db, AnnotatorDocumentUpdate(id=document.id, spacy_applied=True)
        )
        return document

    @classmethod
    def delete(cls, db: DBSession, id: uuid.UUID) -> AnnotatorDocument:
        document = cls.read(db, id)
        session_id = document.session_id
        deleted = super().delete(db, id)
        cls._reindex_documents(db, session_id)
        return deleted
