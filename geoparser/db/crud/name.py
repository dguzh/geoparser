import typing as t
import uuid

from sqlmodel import Session, select

from geoparser.db.crud.base import BaseRepository
from geoparser.db.models.name import Name


class NameRepository(BaseRepository[Name]):
    """
    Repository for Name model operations.
    """

    model = Name

    @classmethod
    def get_by_feature(cls, db: Session, feature_id: uuid.UUID) -> t.List[Name]:
        """
        Get all names for a feature.

        Args:
            db: Database session
            feature_id: ID of the feature

        Returns:
            List of names associated with the feature
        """
        statement = select(Name).where(Name.feature_id == feature_id)
        return db.exec(statement).unique().all()

    @classmethod
    def get_by_name(cls, db: Session, name: str) -> t.List[Name]:
        """
        Get all features with this name.

        Args:
            db: Database session
            name: Name to search for

        Returns:
            List of name records with this name
        """
        statement = select(Name).where(Name.name == name)
        return db.exec(statement).unique().all()
