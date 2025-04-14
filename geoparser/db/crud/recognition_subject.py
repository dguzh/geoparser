import typing as t
import uuid

from sqlalchemy import not_
from sqlmodel import Session, select

from geoparser.db.crud.base import BaseRepository
from geoparser.db.models import Document, RecognitionSubject


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
        return db.exec(statement).unique().all()

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
        return db.exec(statement).unique().all()

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
        return db.exec(statement).unique().first()

    @classmethod
    def get_unprocessed_documents(
        cls, db: Session, project_id: uuid.UUID, module_id: uuid.UUID
    ) -> t.List[Document]:
        """
        Get all documents from a project that have not been processed by a specific module.

        This is done by retrieving all documents for the project and excluding those
        that have a corresponding recognition subject record for the given module.

        Args:
            db: Database session
            project_id: ID of the project containing the documents
            module_id: ID of the recognition module

        Returns:
            List of unprocessed Document objects
        """
        # This query selects all documents from the project where there is no
        # corresponding entry in the recognition_subject table for the given module
        statement = select(Document).where(
            Document.project_id == project_id,
            not_(
                Document.id.in_(
                    select(RecognitionSubject.document_id).where(
                        RecognitionSubject.module_id == module_id
                    )
                )
            ),
        )
        return db.exec(statement).unique().all()
