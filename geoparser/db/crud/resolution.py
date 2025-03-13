import typing as t
import uuid

from sqlmodel import Session, select

from geoparser.db.crud.base import BaseRepository
from geoparser.db.models import Resolution, ResolutionCreate, ResolutionUpdate


class ResolutionRepository(BaseRepository[Resolution]):
    """
    Repository for Resolution model operations.
    """

    model = Resolution

    @classmethod
    def get_by_location(cls, db: Session, location_id: uuid.UUID) -> t.List[Resolution]:
        """
        Get all resolutions for a location.

        Args:
            db: Database session
            location_id: Location ID

        Returns:
            List of resolutions
        """
        statement = select(Resolution).where(Resolution.location_id == location_id)
        return db.exec(statement).all()

    @classmethod
    def get_by_module(cls, db: Session, module_id: uuid.UUID) -> t.List[Resolution]:
        """
        Get all resolutions for a module.

        Args:
            db: Database session
            module_id: Module ID

        Returns:
            List of resolutions
        """
        statement = select(Resolution).where(Resolution.module_id == module_id)
        return db.exec(statement).all()
