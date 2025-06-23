import typing as t

from sqlalchemy import func, literal_column
from sqlmodel import Session, select

from geoparser.db.crud.base import BaseRepository
from geoparser.db.models.feature import Feature
from geoparser.db.models.toponym import Toponym, ToponymFTS


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

    @classmethod
    def get_by_gazetteer_and_toponym_exact(
        cls, db: Session, gazetteer_name: str, toponym: str, limit: int = 1000
    ) -> t.List[Feature]:
        """
        Get all features for a gazetteer that have an exactly matching toponym.

        Uses the FTS table for case-insensitive exact matching. Only returns
        features where the toponym text has exactly the same length as the
        search query.

        Args:
            db: Database session
            gazetteer_name: Name of the gazetteer
            toponym: Toponym string to search for
            limit: Maximum number of results to return (default: 1000)

        Returns:
            List of features that have this exact toponym
        """
        statement = (
            select(Feature)
            .join(Toponym, Feature.id == Toponym.feature_id)
            .join(ToponymFTS, Toponym.id == ToponymFTS.rowid)
            .where(
                Feature.gazetteer_name == gazetteer_name,
                ToponymFTS.text.match(f'"{toponym}"'),
                func.length(Toponym.text) == len(toponym),
            )
            .limit(limit)
        )
        return db.exec(statement).unique().all()

    @classmethod
    def get_by_gazetteer_and_toponym_partial(
        cls,
        db: Session,
        gazetteer_name: str,
        toponym: str,
        limit: int = 1000,
        ranks: int = 1,
    ) -> t.List[Feature]:
        """
        Get all features for a gazetteer that have a toponym containing the search term.

        Uses the FTS table for case-insensitive partial matching with BM25 ranking.
        Returns features where the toponym text contains the search query as a substring.

        Args:
            db: Database session
            gazetteer_name: Name of the gazetteer
            toponym: Toponym string to search for
            limit: Maximum number of results to return (default: 1000)
            ranks: Number of rank groups to include in results (default: 1)

        Returns:
            List of features that have toponyms containing this text, ordered by relevance (highest rank first)
        """
        statement = (
            select(Feature, literal_column("bm25(toponym_fts)").label("rank"))
            .join(Toponym, Feature.id == Toponym.feature_id)
            .join(ToponymFTS, Toponym.id == ToponymFTS.rowid)
            .where(
                Feature.gazetteer_name == gazetteer_name,
                ToponymFTS.text.match(f'"{toponym}"'),
            )
            .order_by(literal_column("bm25(toponym_fts)"))
            .limit(limit)
        )
        results = db.exec(statement).unique().all()

        if not results or ranks <= 0:
            return []

        # Get unique rank values and take only the top N rank groups
        unique_ranks = sorted(list(set(result[1] for result in results)))[:ranks]

        # Filter results to only include features from the top N rank groups
        filtered_results = [
            result[0] for result in results if result[1] in unique_ranks
        ]
        return filtered_results

    @classmethod
    def get_by_gazetteer_and_toponym_fuzzy(
        cls,
        db: Session,
        gazetteer_name: str,
        toponym: str,
        limit: int = 1000,
        ranks: int = 1,
    ) -> t.List[Feature]:
        """
        Get all features for a gazetteer that have toponyms fuzzy matching the search term.

        Uses the FTS table for fuzzy matching by splitting the search term into trigrams
        and searching for any of them with BM25 ranking. This allows for approximate
        matching even with typos or partial character matches.

        Args:
            db: Database session
            gazetteer_name: Name of the gazetteer
            toponym: Toponym string to search for
            limit: Maximum number of results to return (default: 1000)
            ranks: Number of rank groups to include in results (default: 1)

        Returns:
            List of features that have toponyms fuzzy matching this text, ordered by relevance (highest rank first)
        """
        # Generate trigrams for fuzzy matching
        if len(toponym) < 3:
            # For very short strings, fall back to partial matching
            trigram_query = f'"{toponym}"'
        else:
            # Create trigrams and combine with OR
            trigrams = [f'"{toponym[i:i+3]}"' for i in range(len(toponym) - 2)]
            trigram_query = " OR ".join(trigrams)

        statement = (
            select(Feature, literal_column("bm25(toponym_fts)").label("rank"))
            .join(Toponym, Feature.id == Toponym.feature_id)
            .join(ToponymFTS, Toponym.id == ToponymFTS.rowid)
            .where(
                Feature.gazetteer_name == gazetteer_name,
                ToponymFTS.text.match(trigram_query),
            )
            .order_by(literal_column("bm25(toponym_fts)"))
            .limit(limit)
        )
        results = db.exec(statement).unique().all()

        if not results or ranks <= 0:
            return []

        # Get unique rank values and take only the top N rank groups
        unique_ranks = sorted(list(set(result[1] for result in results)))[:ranks]

        # Filter results to only include features from the top N rank groups
        filtered_results = [
            result[0] for result in results if result[1] in unique_ranks
        ]
        return filtered_results
