import typing as t
import uuid

from sqlmodel import Session, select

from geoparser.db.crud.base import BaseRepository
from geoparser.db.models import RecognitionProcess


class RecognitionProcessRepository(BaseRepository[RecognitionProcess]):
    """
    Repository for RecognitionProcess model operations.
    """

    model = RecognitionProcess

    @classmethod
    def get_by_document(
        cls, db: Session, document_id: uuid.UUID
    ) -> t.List[RecognitionProcess]:
        """
        Get all recognition processes for a document.

        Args:
            db: Database session
            document_id: Document ID

        Returns:
            List of recognition processes
        """
        statement = select(RecognitionProcess).where(
            RecognitionProcess.document_id == document_id
        )
        return db.exec(statement).all()

    @classmethod
    def get_by_module(
        cls, db: Session, module_id: uuid.UUID
    ) -> t.List[RecognitionProcess]:
        """
        Get all recognition processes for a module.

        Args:
            db: Database session
            module_id: Recognition module ID

        Returns:
            List of recognition processes
        """
        statement = select(RecognitionProcess).where(
            RecognitionProcess.module_id == module_id
        )
        return db.exec(statement).all() 