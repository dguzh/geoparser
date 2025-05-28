import typing as t

from sqlmodel import Session, select

from geoparser.db.crud.base import BaseRepository
from geoparser.db.models.feature import Feature


class FeatureRepository(BaseRepository[Feature]):
    """
    Repository for Feature model operations.
    """

    model = Feature

    @classmethod
    def get_by_gazetteer(cls, db: Session, gazetteer_name: str) -> t.List[Feature]:
        """
        Get all features for a gazetteer.

        Args:
            db: Database session
            gazetteer_name: Name of the gazetteer

        Returns:
            List of features
        """
        statement = select(Feature).where(Feature.gazetteer_name == gazetteer_name)
        return db.exec(statement).unique().all()

    @classmethod
    def get_by_gazetteer_and_identifier(
        cls, db: Session, gazetteer_name: str, identifier_value: str
    ) -> t.Optional[Feature]:
        """
        Get a feature by gazetteer name and identifier value.

        Args:
            db: Database session
            gazetteer_name: Name of the gazetteer
            identifier_value: Identifier value within that gazetteer

        Returns:
            Feature if found, None otherwise
        """
        statement = select(Feature).where(
            Feature.gazetteer_name == gazetteer_name,
            Feature.identifier_value == identifier_value,
        )
        return db.exec(statement).unique().first()
