import typing as t
import uuid

from sqlmodel import Session, select

from geoparser.db.crud.base import BaseRepository
from geoparser.db.models.source import Source


class SourceRepository(BaseRepository[Source]):
    """
    Repository for Source model operations.
    """

    model = Source

    @classmethod
    def get_by_gazetteer(cls, db: Session, gazetteer_id: uuid.UUID) -> t.List[Source]:
        """
        Get all sources for a gazetteer.

        Args:
            db: Database session
            gazetteer_id: ID of the gazetteer

        Returns:
            List of sources
        """
        statement = select(Source).where(Source.gazetteer_id == gazetteer_id)
        return db.exec(statement).unique().all()

    @classmethod
    def get_by_gazetteer_and_name(
        cls, db: Session, gazetteer_id: uuid.UUID, name: str
    ) -> t.Optional[Source]:
        """
        Get a source by gazetteer ID and name.

        Args:
            db: Database session
            gazetteer_id: ID of the gazetteer
            name: Name of the source (table or view name)

        Returns:
            Source if found, None otherwise
        """
        statement = select(Source).where(
            Source.gazetteer_id == gazetteer_id,
            Source.name == name,
        )
        return db.exec(statement).unique().first()
