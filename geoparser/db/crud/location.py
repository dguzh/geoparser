import typing as t
import uuid

from sqlmodel import Session, select

from geoparser.db.crud.base import BaseRepository
from geoparser.db.models import Location, LocationCreate, LocationUpdate


class LocationRepository(BaseRepository[Location]):
    """
    Repository for Location model operations.
    """

    def __init__(self):
        super().__init__(Location)

    def get_by_toponym(self, db: Session, toponym_id: uuid.UUID) -> t.List[Location]:
        """
        Get all locations for a toponym.

        Args:
            db: Database session
            toponym_id: Toponym ID

        Returns:
            List of locations
        """
        statement = select(Location).where(Location.toponym_id == toponym_id)
        return db.exec(statement).all()
