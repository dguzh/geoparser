import typing as t
from datetime import datetime

from sqlmodel import Session, select

from geoparser.db.crud.base import BaseRepository
from geoparser.db.models import Gazetteer
from geoparser.db.models.gazetteer import GazetteerCreate, GazetteerUpdate


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
            Gazetteer if found, None otherwise
        """
        statement = select(Gazetteer).where(Gazetteer.name == name)
        return db.exec(statement).unique().first()

    @classmethod
    def upsert_by_name(cls, db: Session, name: str) -> Gazetteer:
        """
        Update a gazetteer if it exists, or create it if it doesn't.

        This method updates the installed_at timestamp to the current time.

        Args:
            db: Database session
            name: Name of the gazetteer

        Returns:
            Updated or created Gazetteer
        """
        gazetteer = cls.get_by_name(db, name)

        if gazetteer:
            # Update existing gazetteer with new timestamp
            gazetteer_update = GazetteerUpdate(
                id=gazetteer.id, name=name, installed_at=datetime.utcnow()
            )
            return cls.update(db, db_obj=gazetteer, obj_in=gazetteer_update)
        else:
            # Create new gazetteer
            gazetteer_create = GazetteerCreate(
                name=name, installed_at=datetime.utcnow()
            )
            return cls.create(db, gazetteer_create)
