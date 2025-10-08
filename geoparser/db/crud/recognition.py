import typing as t
import uuid

from sqlalchemy import not_
from sqlmodel import Session, select

from geoparser.db.crud.base import BaseRepository
from geoparser.db.models import Document, Recognition


class RecognitionRepository(BaseRepository[Recognition]):
    """
    Repository for Recognition model operations.
    """

    model = Recognition

    @classmethod
    def get_by_document(
        cls, db: Session, document_id: uuid.UUID
    ) -> t.List[Recognition]:
        """
        Get all recognitions for a document.

        Args:
            db: Database session
            document_id: ID of the document

        Returns:
            List of recognitions
        """
        statement = select(Recognition).where(Recognition.document_id == document_id)
        return db.exec(statement).unique().all()

    @classmethod
    def get_by_recognizer(cls, db: Session, recognizer_id: str) -> t.List[Recognition]:
        """
        Get all recognitions for a recognizer.

        Args:
            db: Database session
            recognizer_id: ID of the recognizer

        Returns:
            List of recognitions
        """
        statement = select(Recognition).where(
            Recognition.recognizer_id == recognizer_id
        )
        return db.exec(statement).unique().all()

    @classmethod
    def get_by_document_and_recognizer(
        cls, db: Session, document_id: uuid.UUID, recognizer_id: str
    ) -> t.Optional[Recognition]:
        """
        Get a recognition for a specific document and recognizer.

        Args:
            db: Database session
            document_id: ID of the document
            recognizer_id: ID of the recognizer

        Returns:
            Recognition if found, None otherwise
        """
        statement = select(Recognition).where(
            Recognition.document_id == document_id,
            Recognition.recognizer_id == recognizer_id,
        )
        return db.exec(statement).unique().first()

    @classmethod
    def get_unprocessed_documents(
        cls, db: Session, project_id: uuid.UUID, recognizer_id: str
    ) -> t.List[Document]:
        """
        Get all documents from a project that have not been processed by a specific recognizer.

        This is done by retrieving all documents for the project and excluding those
        that have a corresponding recognition record for the given recognizer.

        Args:
            db: Database session
            project_id: ID of the project containing the documents
            recognizer_id: ID of the recognizer

        Returns:
            List of unprocessed Document objects
        """
        # This query selects all documents from the project where there is no
        # corresponding entry in the recognition table for the given recognizer
        statement = select(Document).where(
            Document.project_id == project_id,
            not_(
                Document.id.in_(
                    select(Recognition.document_id).where(
                        Recognition.recognizer_id == recognizer_id
                    )
                )
            ),
        )
        return db.exec(statement).unique().all()
