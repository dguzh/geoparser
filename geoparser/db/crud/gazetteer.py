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
        Get a gazetteer by name.

        Args:
            db: Database session
            name: Name of the gazetteer

        Returns:
            Gazetteer object if found, None otherwise
        """
        statement = select(Gazetteer).where(Gazetteer.name == name)
        return db.exec(statement).unique().first()
