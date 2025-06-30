import typing as t
import uuid

from sqlmodel import Session, select

from geoparser.db.crud.base import BaseRepository
from geoparser.db.models import ResolutionObject


class ResolutionObjectRepository(BaseRepository[ResolutionObject]):
    """
    Repository for ResolutionObject model operations.
    """

    model = ResolutionObject

    @classmethod
    def get_by_referent(
        cls, db: Session, referent_id: uuid.UUID
    ) -> t.List[ResolutionObject]:
        """
        Get all resolution objects for a referent.

        Args:
            db: Database session
            referent_id: ID of the referent

        Returns:
            List of resolution objects
        """
        statement = select(ResolutionObject).where(
            ResolutionObject.referent_id == referent_id
        )
        return db.exec(statement).unique().all()

    @classmethod
    def get_by_module(
        cls, db: Session, module_id: uuid.UUID
    ) -> t.List[ResolutionObject]:
        """
        Get all resolution objects for a module.

        Args:
            db: Database session
            module_id: ID of the resolution module

        Returns:
            List of resolution objects
        """
        statement = select(ResolutionObject).where(
            ResolutionObject.module_id == module_id
        )
        return db.exec(statement).unique().all()

    @classmethod
    def get_by_referent_and_module(
        cls, db: Session, referent_id: uuid.UUID, module_id: uuid.UUID
    ) -> t.Optional[ResolutionObject]:
        """
        Get a resolution object for a specific referent and module.

        Args:
            db: Database session
            referent_id: ID of the referent
            module_id: ID of the resolution module

        Returns:
            Resolution object if found, None otherwise
        """
        statement = select(ResolutionObject).where(
            ResolutionObject.referent_id == referent_id,
            ResolutionObject.module_id == module_id,
        )
        return db.exec(statement).unique().first()
