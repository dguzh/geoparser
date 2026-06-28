import typing as t

from sqlalchemy import func
from sqlmodel import Session, select

from geoparser.db.crud.base import BaseRepository
from geoparser.db.models.feature import Feature
from geoparser.db.models.gazetteer import Gazetteer
from geoparser.db.models.name import Name
from geoparser.db.models.source import Source


class NameRepository(BaseRepository[Name]):
    """
    Repository for Name model operations.
    """

    model = Name

    @classmethod
    def get_by_feature(cls, db: Session, feature_id: int) -> t.List[Name]:
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
        statement = select(Name).where(Name.text == name)
        return db.exec(statement).unique().all()

    @classmethod
    def count_by_gazetteer(cls, db: Session, gazetteer_name: str) -> int:
        """
        Count names registered for a gazetteer.

        Args:
            db: Database session
            gazetteer_name: Name of the gazetteer

        Returns:
            Number of registered names
        """
        statement = (
            select(func.count())
            .select_from(Name)
            .join(Feature, Name.feature_id == Feature.id)
            .join(Source, Feature.source_id == Source.id)
            .join(Gazetteer, Source.gazetteer_id == Gazetteer.id)
            .where(Gazetteer.name == gazetteer_name)
        )
        return db.exec(statement).one()
