import typing as t
import uuid

from sqlmodel import Session, select

from geoparser.db.crud.base import BaseRepository
from geoparser.db.models import ResolutionSubject


class ResolutionSubjectRepository(BaseRepository[ResolutionSubject]):
    """
    Repository for ResolutionSubject model operations.
    """

    model = ResolutionSubject

    @classmethod
    def get_by_toponym(
        cls, db: Session, toponym_id: uuid.UUID
    ) -> t.List[ResolutionSubject]:
        """
        Get all resolution subjects for a toponym.

        Args:
            db: Database session
            toponym_id: ID of the toponym

        Returns:
            List of resolution subjects
        """
        statement = select(ResolutionSubject).where(
            ResolutionSubject.toponym_id == toponym_id
        )
        return db.exec(statement).all()

    @classmethod
    def get_by_module(
        cls, db: Session, module_id: uuid.UUID
    ) -> t.List[ResolutionSubject]:
        """
        Get all resolution subjects for a module.

        Args:
            db: Database session
            module_id: ID of the resolution module

        Returns:
            List of resolution subjects
        """
        statement = select(ResolutionSubject).where(
            ResolutionSubject.module_id == module_id
        )
        return db.exec(statement).all()

    @classmethod
    def get_by_toponym_and_module(
        cls, db: Session, toponym_id: uuid.UUID, module_id: uuid.UUID
    ) -> t.Optional[ResolutionSubject]:
        """
        Get a resolution subject for a specific toponym and module.

        Args:
            db: Database session
            toponym_id: ID of the toponym
            module_id: ID of the resolution module

        Returns:
            ResolutionSubject if found, None otherwise
        """
        statement = select(ResolutionSubject).where(
            ResolutionSubject.toponym_id == toponym_id,
            ResolutionSubject.module_id == module_id,
        )
        return db.exec(statement).first() 