import typing as t
import uuid

from sqlmodel import Session, select

from geoparser.db.crud.base import BaseRepository
from geoparser.db.models.gazetteer_table import GazetteerTable


class GazetteerTableRepository(BaseRepository[GazetteerTable]):
    """
    Repository for GazetteerTable model operations.
    """

    model = GazetteerTable

    @classmethod
    def get_by_gazetteer(
        cls, db: Session, gazetteer_id: uuid.UUID
    ) -> t.List[GazetteerTable]:
        """
        Get all tables for a gazetteer by ID.

        Args:
            db: Database session
            gazetteer_id: ID of the gazetteer

        Returns:
            List of GazetteerTable objects
        """
        statement = select(GazetteerTable).where(
            GazetteerTable.gazetteer_id == gazetteer_id
        )
        return db.exec(statement).unique().all()
