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
    def get_by_name(cls, db: Session, name: str) -> t.List[Gazetteer]:
        """
        Get all gazetteers with the given name.

        Args:
            db: Database session
            name: Name of the gazetteer

        Returns:
            List of Gazetteer objects
        """
        statement = select(Gazetteer).where(Gazetteer.name == name)
        return db.exec(statement).unique().all()
