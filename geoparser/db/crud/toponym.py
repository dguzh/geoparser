import typing as t

from sqlmodel import Session, select

from geoparser.db.crud.base import BaseRepository
from geoparser.db.models.toponym import Toponym


class ToponymRepository(BaseRepository[Toponym]):
    """
    Repository for Toponym model operations.
    """

    model = Toponym

    @classmethod
    def get_by_feature(cls, db: Session, feature_id: int) -> t.List[Toponym]:
        """
        Get all toponyms for a feature.

        Args:
            db: Database session
            feature_id: ID of the feature

        Returns:
            List of toponyms associated with the feature
        """
        statement = select(Toponym).where(Toponym.feature_id == feature_id)
        return db.exec(statement).unique().all()

    @classmethod
    def get_by_toponym(cls, db: Session, toponym: str) -> t.List[Toponym]:
        """
        Get all features with this toponym.

        Args:
            db: Database session
            toponym: Toponym to search for

        Returns:
            List of toponym records with this toponym
        """
        statement = select(Toponym).where(Toponym.toponym == toponym)
        return db.exec(statement).unique().all()
