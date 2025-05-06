import typing as t
import uuid

from sqlmodel import Session, select

from geoparser.db.crud.base import BaseRepository
from geoparser.db.models.gazetteer_column import GazetteerColumn


class GazetteerColumnRepository(BaseRepository[GazetteerColumn]):
    """
    Repository for GazetteerColumn model operations.
    """

    model = GazetteerColumn

    @classmethod
    def get_by_table(cls, db: Session, table_id: uuid.UUID) -> t.List[GazetteerColumn]:
        """
        Get all columns for a table by ID.

        Args:
            db: Database session
            table_id: ID of the table

        Returns:
            List of GazetteerColumn objects
        """
        statement = select(GazetteerColumn).where(GazetteerColumn.table_id == table_id)
        return db.exec(statement).unique().all()

    @classmethod
    def get_by_name_and_table(
        cls, db: Session, table_id: uuid.UUID, name: str
    ) -> t.Optional[GazetteerColumn]:
        """
        Get a column by name and table ID.

        Args:
            db: Database session
            table_id: ID of the table
            name: Name of the column

        Returns:
            GazetteerColumn if found, None otherwise
        """
        statement = select(GazetteerColumn).where(
            GazetteerColumn.table_id == table_id, GazetteerColumn.name == name
        )
        return db.exec(statement).unique().first()
