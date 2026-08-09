import typing as t
import uuid

from sqlmodel import Session, select

from geoparser.db.crud.base import BaseRepository
from geoparser.db.models import Document


class DocumentRepository(BaseRepository[Document]):
    """
    Repository for Document model operations.
    """

    model = Document

    @classmethod
    def get_by_project(cls, db: Session, project_id: uuid.UUID) -> t.List[Document]:
        """
        Get all documents for a project.

        Args:
            db: Database session
            project_id: Project ID

        Returns:
            List of documents
        """
        statement = select(Document).where(Document.project_id == project_id)
        return db.exec(statement).unique().all()

    @classmethod
    def get_by_ids(
        cls, db: Session, project_id: uuid.UUID, ids: t.Sequence[uuid.UUID]
    ) -> t.List[Document]:
        """
        Get the documents with the given IDs that belong to a project.

        IDs that do not exist or belong to another project are ignored, and the
        results are returned in no particular order.

        Args:
            db: Database session
            project_id: Project ID
            ids: Document IDs to retrieve

        Returns:
            List of documents
        """
        documents = []

        # Query in chunks to stay below the SQLite limit on bound parameters
        chunk_size = 500
        for offset in range(0, len(ids), chunk_size):
            chunk = ids[offset : offset + chunk_size]
            statement = select(Document).where(
                Document.project_id == project_id, Document.id.in_(chunk)
            )
            documents.extend(db.exec(statement).unique().all())

        return documents
