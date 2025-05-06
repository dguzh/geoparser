import typing as t
import uuid

from sqlmodel import Session, select

from geoparser.db.crud.base import BaseRepository
from geoparser.db.models.gazetteer_relationship import GazetteerRelationship


class GazetteerRelationshipRepository(BaseRepository[GazetteerRelationship]):
    """
    Repository for GazetteerRelationship model operations.
    """

    model = GazetteerRelationship

    @classmethod
    def get_by_gazetteer(
        cls, db: Session, gazetteer_id: uuid.UUID
    ) -> t.List[GazetteerRelationship]:
        """
        Get all relationships for a gazetteer by ID.

        Args:
            db: Database session
            gazetteer_id: ID of the gazetteer

        Returns:
            List of GazetteerRelationship objects
        """
        statement = select(GazetteerRelationship).where(
            GazetteerRelationship.gazetteer_id == gazetteer_id
        )
        return db.exec(statement).unique().all()
