import typing as t
import uuid

from sqlmodel import Session, select

from geoparser.db.crud.base import BaseRepository
from geoparser.db.models import Toponym
from geoparser.db.models.document import Document
from geoparser.db.models.toponym import ToponymCreate


class ToponymRepository(BaseRepository[Toponym]):
    """
    Repository for Toponym model operations.
    """

    model = Toponym

    @classmethod
    def create(cls, db: Session, obj_in: ToponymCreate) -> Toponym:
        """
        Create a new toponym and populate its text field from the document.

        Args:
            db: Database session
            obj_in: ToponymCreate instance with document_id, start and end positions

        Returns:
            Created toponym with populated text field
        """
        # Extract data from the ToponymCreate model
        data = obj_in.model_dump()
        document_id = data["document_id"]
        start = data["start"]
        end = data["end"]

        # Get the document to extract the text
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
