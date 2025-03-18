import typing as t
import uuid

from sqlmodel import Session, select

from geoparser.db.crud.base import BaseRepository
from geoparser.db.models import RecognitionSubject


class RecognitionSubjectRepository(BaseRepository[RecognitionSubject]):
    """
    Repository for RecognitionSubject model operations.
    """

    model = RecognitionSubject

    @classmethod
    def get_by_document(
        cls, db: Session, document_id: uuid.UUID
    ) -> t.List[RecognitionSubject]:
        """
        Get all recognition subjects for a document.

        Args:
            db: Database session
            document_id: ID of the document

        Returns:
            List of recognition subjects
        """
        statement = select(RecognitionSubject).where(
            RecognitionSubject.document_id == document_id
        )
        return db.exec(statement).all()

    @classmethod
    def get_by_module(
        cls, db: Session, module_id: uuid.UUID
    ) -> t.List[RecognitionSubject]:
        """
        Get all recognition subjects for a module.

        Args:
            db: Database session
            module_id: ID of the recognition module

        Returns:
            List of recognition subjects
        """
        statement = select(RecognitionSubject).where(
            RecognitionSubject.module_id == module_id
        )
        return db.exec(statement).all()

    @classmethod
    def get_by_document_and_module(
        cls, db: Session, document_id: uuid.UUID, module_id: uuid.UUID
    ) -> t.Optional[RecognitionSubject]:
        """
        Get a recognition subject for a specific document and module.

        Args:
            db: Database session
            document_id: ID of the document
            module_id: ID of the recognition module

        Returns:
            RecognitionSubject if found, None otherwise
        """
        statement = select(RecognitionSubject).where(
            RecognitionSubject.document_id == document_id,
            RecognitionSubject.module_id == module_id,
        )
        return db.exec(statement).first() 