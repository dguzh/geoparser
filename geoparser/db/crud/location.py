import typing as t
import uuid

from sqlmodel import Session, select

from geoparser.db.crud.base import BaseRepository
from geoparser.db.models import Location


class LocationRepository(BaseRepository[Location]):
    """
    Repository for Location model operations.
    """

    model = Location

    @classmethod
    def get_by_toponym(cls, db: Session, toponym_id: uuid.UUID) -> t.List[Location]:
        """
        Get all locations for a toponym.

        Args:
            db: Database session
            toponym_id: Toponym ID

        Returns:
            List of locations
        """
        statement = select(Location).where(Location.toponym_id == toponym_id)
        return db.exec(statement).unique().all()
