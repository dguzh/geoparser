import typing as t
import uuid

from sqlmodel import Session, select

from geoparser.db.crud.base import BaseRepository
from geoparser.db.models import Toponym
from geoparser.db.models.document import Document


class ToponymRepository(BaseRepository[Toponym]):
    """
    Repository for Toponym model operations.
    """

    model = Toponym

    @classmethod
    def create(cls, db: Session, obj_in: t.Union[dict, Toponym]) -> Toponym:
        """
        Create a new toponym and populate its text field from the document.

        Args:
            db: Database session
            obj_in: Toponym data to create or Toponym instance

        Returns:
            Created toponym with populated text field
        """
        # First, ensure we're working with a dict
        if isinstance(obj_in, Toponym):
            data = {
                "document_id": obj_in.document_id,
                "start": obj_in.start,
                "end": obj_in.end,
            }
        else:
            data = obj_in.copy() if isinstance(obj_in, dict) else obj_in.model_dump()

        # Get the document to extract the text
        document_id = data.get("document_id")
        start = data.get("start")
        end = data.get("end")

        # Get the document
        document = db.get(Document, document_id)
        if document and hasattr(document, "text"):
            # Extract the text from the document using the span
            data["text"] = document.text[start:end]

        # Create the toponym with the added text field
        return super().create(db, Toponym(**data))

    @classmethod
    def get_by_document(cls, db: Session, document_id: uuid.UUID) -> t.List[Toponym]:
        """
        Get all toponyms for a document.

        Args:
            db: Database session
            document_id: Document ID

        Returns:
            List of toponyms
        """
        statement = select(Toponym).where(Toponym.document_id == document_id)
        return db.exec(statement).all()

    @classmethod
    def get_by_document_and_span(
        cls, db: Session, document_id: uuid.UUID, start: int, end: int
    ) -> t.Optional[Toponym]:
        """
        Get a toponym by document ID and span (start and end positions).

        Args:
            db: Database session
            document_id: Document ID
            start: Start position of the toponym
            end: End position of the toponym

        Returns:
            Toponym if found, None otherwise
        """
        statement = select(Toponym).where(
            Toponym.document_id == document_id,
            Toponym.start == start,
            Toponym.end == end,
        )
        return db.exec(statement).first()
