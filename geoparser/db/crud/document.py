import typing as t
import uuid

from sqlmodel import Session, select

from geoparser.db.crud.base import BaseRepository
from geoparser.db.models import Document, DocumentCreate, DocumentUpdate


class DocumentRepository(BaseRepository[Document]):
    """
    Repository for Document model operations.
    """

    def __init__(self):
        super().__init__(Document)

    def get_by_session(self, db: Session, session_id: uuid.UUID) -> t.List[Document]:
        """
        Get all documents for a session.

        Args:
            db: Database session
            session_id: Session ID

        Returns:
            List of documents
        """
        statement = select(Document).where(Document.session_id == session_id)
        return db.exec(statement).all()
