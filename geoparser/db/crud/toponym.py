import typing as t
import uuid

from sqlmodel import Session, select

from geoparser.db.crud.base import BaseRepository
from geoparser.db.models import Toponym, ToponymCreate, ToponymUpdate


class ToponymRepository(BaseRepository[Toponym]):
    """
    Repository for Toponym model operations.
    """

    def __init__(self):
        super().__init__(Toponym)

    def get_by_document(self, db: Session, document_id: uuid.UUID) -> t.List[Toponym]:
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


toponym_repository = ToponymRepository()
