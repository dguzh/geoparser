import typing as t
import uuid

from sqlmodel import Session as DBSession, select
from sqlalchemy import not_

from geoparser.db.crud.base import BaseRepository
from geoparser.db.models import RecognitionSubject, Document


class RecognitionSubjectRepository(BaseRepository[RecognitionSubject]):
    """
    Repository for RecognitionSubject model operations.
    """

    model = RecognitionSubject

    @classmethod
    def get_by_document(
        cls, db: DBSession, document_id: uuid.UUID
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
        cls, db: DBSession, module_id: uuid.UUID
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
        cls, db: DBSession, document_id: uuid.UUID, module_id: uuid.UUID
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
        
    @classmethod
    def get_unprocessed_documents(
        cls, db: DBSession, session_id: uuid.UUID, module_id: uuid.UUID
    ) -> t.List[Document]:
        """
        Get all documents from a session that have not been processed by a specific module.
        
        This is done by retrieving all documents for the session and excluding those
        that have a corresponding recognition subject record for the given module.
        
        Args:
            db: Database session
            session_id: ID of the session containing the documents
            module_id: ID of the recognition module
            
        Returns:
            List of unprocessed Document objects
        """
        # This query selects all documents from the session where there is no
        # corresponding entry in the recognition_subject table for the given module
        statement = select(Document).where(
            Document.session_id == session_id,
            not_(
                Document.id.in_(
                    select(RecognitionSubject.document_id).where(
                        RecognitionSubject.module_id == module_id
                    )
                )
            )
        )
        return db.exec(statement).all()
        
    @classmethod
    def create_many(
        cls, db: DBSession, document_ids: t.List[uuid.UUID], module_id: uuid.UUID
    ) -> t.List[RecognitionSubject]:
        """
        Create multiple recognition subject records at once.
        
        Args:
            db: Database session
            document_ids: List of document IDs
            module_id: ID of the recognition module
            
        Returns:
            List of created RecognitionSubject objects
        """
        subjects = []
        for document_id in document_ids:
            subject = RecognitionSubject(document_id=document_id, module_id=module_id)
            db.add(subject)
            subjects.append(subject)
        
        db.flush()  # Flush to assign IDs but don't commit yet
        return subjects 