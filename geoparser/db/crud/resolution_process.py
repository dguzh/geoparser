import typing as t
import uuid

from sqlmodel import Session, select

from geoparser.db.crud.base import BaseRepository
from geoparser.db.models import ResolutionProcess


class ResolutionProcessRepository(BaseRepository[ResolutionProcess]):
    """
    Repository for ResolutionProcess model operations.
    """

    model = ResolutionProcess

    @classmethod
    def get_by_toponym(
        cls, db: Session, toponym_id: uuid.UUID
    ) -> t.List[ResolutionProcess]:
        """
        Get all resolution processes for a toponym.

        Args:
            db: Database session
            toponym_id: Toponym ID

        Returns:
            List of resolution processes
        """
        statement = select(ResolutionProcess).where(
            ResolutionProcess.toponym_id == toponym_id
        )
        return db.exec(statement).all()

    @classmethod
    def get_by_module(
        cls, db: Session, module_id: uuid.UUID
    ) -> t.List[ResolutionProcess]:
        """
        Get all resolution processes for a module.

        Args:
            db: Database session
            module_id: Resolution module ID

        Returns:
            List of resolution processes
        """
        statement = select(ResolutionProcess).where(
            ResolutionProcess.module_id == module_id
        )
        return db.exec(statement).all() 