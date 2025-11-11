import typing as t
import uuid

from sqlmodel import Session, select

from geoparser.db.crud.base import BaseRepository
from geoparser.db.models import Reference
from geoparser.db.models.document import Document
from geoparser.db.models.reference import ReferenceCreate, ReferenceUpdate


class ReferenceRepository(BaseRepository[Reference]):
    """
    Repository for Reference model operations.
    """

    model = Reference

    @classmethod
    def create(cls, db: Session, obj_in: ReferenceCreate) -> Reference:
        """
        Create a new reference and populate its text field from the document.

        Args:
            db: Database session
            obj_in: ReferenceCreate instance with document_id, start and end positions

        Returns:
            Created reference with populated text field
        """
        # Extract data from the ReferenceCreate model
        data = obj_in.model_dump()
        document_id = data["document_id"]
        recognizer_id = data["recognizer_id"]
        start = data["start"]
        end = data["end"]

        # Get the document to extract the text
        document = db.get(Document, document_id)
        if document and hasattr(document, "text"):
            # Extract the text from the document using the span
            data["text"] = document.text[start:end]

        # Create the reference with the added text field
        return super().create(db, Reference(**data))

    @classmethod
    def update(
        cls, db: Session, *, db_obj: Reference, obj_in: ReferenceUpdate
    ) -> Reference:
        """
        Update a reference and refresh its text field.

        Args:
            db: Database session
            db_obj: Existing reference to update
            obj_in: ReferenceUpdate with new data

        Returns:
            Updated reference with refreshed text field
        """
        # Get update data
        update_data = obj_in.model_dump(exclude_unset=True)

        # Determine the new positions and document
        start = update_data.get("start", db_obj.start)
        end = update_data.get("end", db_obj.end)
        document_id = update_data.get("document_id", db_obj.document_id)
        recognizer_id = update_data.get("recognizer_id", db_obj.recognizer_id)

        # Get the document to extract updated text
        document = db.get(Document, document_id)
        if document and hasattr(document, "text"):
            # Update the text field
            update_data["text"] = document.text[start:end]

        return super().update(db, db_obj=db_obj, obj_in=Reference(**update_data))

    @classmethod
    def get_by_document(cls, db: Session, document_id: uuid.UUID) -> t.List[Reference]:
        """
        Get all references for a document.

        Args:
            db: Database session
            document_id: Document ID

        Returns:
            List of references
        """
        statement = select(Reference).where(Reference.document_id == document_id)
        return db.exec(statement).unique().all()

    @classmethod
    def get_by_document_and_span(
        cls, db: Session, document_id: uuid.UUID, start: int, end: int
    ) -> t.Optional[Reference]:
        """
        Get a reference by document ID and span (start and end positions).

        Args:
            db: Database session
            document_id: Document ID
            start: Start position of the reference
            end: End position of the reference

        Returns:
            Reference if found, None otherwise
        """
        statement = select(Reference).where(
            Reference.document_id == document_id,
            Reference.start == start,
            Reference.end == end,
        )
        return db.exec(statement).unique().first()
