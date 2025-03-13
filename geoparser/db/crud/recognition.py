import typing as t
import uuid

from sqlmodel import Session, select

from geoparser.db.crud.base import BaseRepository
from geoparser.db.models import Recognition, RecognitionCreate, RecognitionUpdate


class RecognitionRepository(BaseRepository[Recognition]):
    """
    Repository for Recognition model operations.
    """

    def __init__(self):
        super().__init__(Recognition)

    def get_by_toponym(self, db: Session, toponym_id: uuid.UUID) -> t.List[Recognition]:
        """
        Get all recognitions for a toponym.

        Args:
            db: Database session
            toponym_id: Toponym ID

        Returns:
            List of recognitions
        """
        statement = select(Recognition).where(Recognition.toponym_id == toponym_id)
        return db.exec(statement).all()

    def get_by_module(self, db: Session, module_id: uuid.UUID) -> t.List[Recognition]:
        """
        Get all recognitions for a module.

        Args:
            db: Database session
            module_id: Module ID

        Returns:
            List of recognitions
        """
        statement = select(Recognition).where(Recognition.module_id == module_id)
        return db.exec(statement).all()
