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
    def get_by_location(
        cls, db: Session, location_id: uuid.UUID
    ) -> t.List[ResolutionObject]:
        """
        Get all resolution objects for a location.

        Args:
            db: Database session
            location_id: ID of the location

        Returns:
            List of resolution objects
        """
        statement = select(ResolutionObject).where(
            ResolutionObject.location_id == location_id
        )
        return db.exec(statement).all()

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
        return db.exec(statement).all()

    @classmethod
    def get_by_location_and_module(
        cls, db: Session, location_id: uuid.UUID, module_id: uuid.UUID
    ) -> t.Optional[ResolutionObject]:
        """
        Get a resolution object for a specific location and module.

        Args:
            db: Database session
            location_id: ID of the location
            module_id: ID of the resolution module

        Returns:
            Resolution object if found, None otherwise
        """
        statement = select(ResolutionObject).where(
            ResolutionObject.location_id == location_id,
            ResolutionObject.module_id == module_id,
        )
        return db.exec(statement).first()
