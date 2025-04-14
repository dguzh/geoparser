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
