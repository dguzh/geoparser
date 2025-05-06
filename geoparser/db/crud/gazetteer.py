import typing as t

from sqlmodel import Session, select

from geoparser.db.crud.base import BaseRepository
from geoparser.db.models import Gazetteer


class GazetteerRepository(BaseRepository[Gazetteer]):
    """
    Repository for Gazetteer model operations.
    """

    model = Gazetteer

    @classmethod
    def get_by_name(cls, db: Session, name: str) -> t.Optional[Gazetteer]:
        """
        Get the most recent gazetteer with the given name.

        Args:
            db: Database session
            name: Name of the gazetteer

        Returns:
            Gazetteer if found, None otherwise
        """
        statement = (
            select(Gazetteer)
            .where(Gazetteer.name == name)
            .order_by(Gazetteer.modified.desc())
        )
        return db.exec(statement).unique().first()
