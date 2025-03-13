import typing as t
import uuid

from sqlmodel import Session, select

from geoparser.db.crud.base import BaseRepository
from geoparser.db.models import Toponym


class ToponymRepository(BaseRepository[Toponym]):
    """
    Repository for Toponym model operations.
    """

    model = Toponym

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
