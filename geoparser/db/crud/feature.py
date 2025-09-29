import typing as t

from sqlalchemy import func, literal_column
from sqlmodel import Session, select

from geoparser.db.crud.base import BaseRepository
from geoparser.db.models.feature import Feature
from geoparser.db.models.name import Name, NameFTSTrigrams, NameFTSWords


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
    def get_by_gazetteer_and_name_exact(
        cls, db: Session, gazetteer_name: str, name: str, limit: int = 1000
    ) -> t.List[Feature]:
        """
        Get all features for a gazetteer that have an exactly matching name.

        Uses the unicode61 FTS table for case-insensitive exact matching. Only returns
        features where the name text has exactly the same length as the
        search query.

        Args:
            db: Database session
            gazetteer_name: Name of the gazetteer
            name: Name string to search for
            limit: Maximum number of results to return (default: 1000)

        Returns:
            List of features that have this exact name
        """
        query = f'"{name}"'

        statement = (
            select(Feature)
            .join(Name, Feature.id == Name.feature_id)
            .join(NameFTSWords, Name.id == NameFTSWords.rowid)
            .where(
                Feature.gazetteer_name == gazetteer_name,
                NameFTSWords.text.match(query),
                func.length(Name.text) == len(name),
            )
            .limit(limit)
        )
        return db.exec(statement).unique().all()

    @classmethod
    def get_by_gazetteer_and_name_phrase(
        cls,
        db: Session,
        gazetteer_name: str,
        name: str,
        limit: int = 1000,
        ranks: int = 1,
    ) -> t.List[Feature]:
        """
        Get all features for a gazetteer that have a name containing the search term as a phrase.

        Uses the unicode61 FTS table for phrase matching with BM25 ranking.
        Returns features where the name text contains the search query as a contiguous phrase
        (subspan) in the exact word order specified.

        Args:
            db: Database session
            gazetteer_name: Name of the gazetteer
            name: Name string to search for
            limit: Maximum number of results to return (default: 1000)
            ranks: Number of rank groups to include in results (default: 1)

        Returns:
            List of features that have names containing this text as a phrase, ordered by relevance (highest rank first)
        """
        query = f'"{name}"'

        statement = (
            select(Feature, literal_column("bm25(name_fts_words)").label("rank"))
            .join(Name, Feature.id == Name.feature_id)
            .join(NameFTSWords, Name.id == NameFTSWords.rowid)
            .where(
                Feature.gazetteer_name == gazetteer_name,
                NameFTSWords.text.match(query),
            )
            .order_by(literal_column("bm25(name_fts_words)"))
            .limit(limit)
        )
        results = db.exec(statement).unique().all()

        return cls._filter_by_ranks(results, ranks)

    @classmethod
    def get_by_gazetteer_and_name_permuted(
        cls,
        db: Session,
        gazetteer_name: str,
        name: str,
        limit: int = 1000,
        ranks: int = 1,
    ) -> t.List[Feature]:
        """
        Get all features for a gazetteer that have a name containing all search terms in any order.

        Uses the unicode61 FTS table for permuted token matching with BM25 ranking.
        Returns features where the name text contains all tokens from the search query,
        but the order of tokens doesn't matter (implicit AND).

        Args:
            db: Database session
            gazetteer_name: Name of the gazetteer
            name: Name string to search for
            limit: Maximum number of results to return (default: 1000)
            ranks: Number of rank groups to include in results (default: 1)

        Returns:
            List of features that have names containing all search tokens in any order, ordered by relevance (highest rank first)
        """
        query = " ".join(
            [f'"{token.strip()}"' for token in name.split() if token.strip()]
        )

        statement = (
            select(Feature, literal_column("bm25(name_fts_words)").label("rank"))
            .join(Name, Feature.id == Name.feature_id)
            .join(NameFTSWords, Name.id == NameFTSWords.rowid)
            .where(
                Feature.gazetteer_name == gazetteer_name,
                NameFTSWords.text.match(query),
            )
            .order_by(literal_column("bm25(name_fts_words)"))
            .limit(limit)
        )
        results = db.exec(statement).unique().all()

        return cls._filter_by_ranks(results, ranks)

    @classmethod
    def get_by_gazetteer_and_name_partial(
        cls,
        db: Session,
        gazetteer_name: str,
        name: str,
        limit: int = 1000,
        ranks: int = 1,
    ) -> t.List[Feature]:
        """
        Get all features for a gazetteer that have a name partially matching the search terms.

        Uses the unicode61 FTS table for partial token matching with BM25 ranking.
        Returns features where the name text contains some (but not necessarily all)
        tokens from the search query using OR logic for looser matching.

        Args:
            db: Database session
            gazetteer_name: Name of the gazetteer
            name: Name string to search for
            limit: Maximum number of results to return (default: 1000)
            ranks: Number of rank groups to include in results (default: 1)

        Returns:
            List of features that have names partially matching the search tokens, ordered by relevance (highest rank first)
        """
        query = " OR ".join(
            [f'"{token.strip()}"' for token in name.split() if token.strip()]
        )

        statement = (
            select(Feature, literal_column("bm25(name_fts_words)").label("rank"))
            .join(Name, Feature.id == Name.feature_id)
            .join(NameFTSWords, Name.id == NameFTSWords.rowid)
            .where(
                Feature.gazetteer_name == gazetteer_name,
                NameFTSWords.text.match(query),
            )
            .order_by(literal_column("bm25(name_fts_words)"))
            .limit(limit)
        )
        results = db.exec(statement).unique().all()

        return cls._filter_by_ranks(results, ranks)

    @classmethod
    def get_by_gazetteer_and_name_substring(
        cls,
        db: Session,
        gazetteer_name: str,
        name: str,
        limit: int = 1000,
        ranks: int = 1,
    ) -> t.List[Feature]:
        """
        Get all features for a gazetteer that have a name containing the search term as a substring.

        Uses the trigram FTS table for character-level substring matching with BM25 ranking.
        Returns features where the name text contains character sequences matching the search query.
        Note: This method requires queries with 3 or more characters due to trigram tokenization.

        Args:
            db: Database session
            gazetteer_name: Name of the gazetteer
            name: Name string to search for
            limit: Maximum number of results to return (default: 1000)
            ranks: Number of rank groups to include in results (default: 1)

        Returns:
            List of features that have names containing this text as a substring, ordered by relevance (highest rank first)
        """
        # Trigram tokenization requires at least 3 characters
        if len(name) < 3:
            return []

        query = f'"{name}"'

        statement = (
            select(Feature, literal_column("bm25(name_fts_trigrams)").label("rank"))
            .join(Name, Feature.id == Name.feature_id)
            .join(NameFTSTrigrams, Name.id == NameFTSTrigrams.rowid)
            .where(
                Feature.gazetteer_name == gazetteer_name,
                NameFTSTrigrams.text.match(query),
            )
            .order_by(literal_column("bm25(name_fts_trigrams)"))
            .limit(limit)
        )
        results = db.exec(statement).unique().all()

        return cls._filter_by_ranks(results, ranks)

    @classmethod
    def get_by_gazetteer_and_name_fuzzy(
        cls,
        db: Session,
        gazetteer_name: str,
        name: str,
        limit: int = 1000,
        ranks: int = 1,
    ) -> t.List[Feature]:
        """
        Get all features for a gazetteer that have names fuzzy matching the search term.

        Uses the trigram FTS table for fuzzy matching by splitting the search term into trigrams
        and searching for any of them with BM25 ranking. This allows for approximate
        matching even with typos or partial character matches.
        Note: This method requires queries with 3 or more characters due to trigram tokenization.

        Args:
            db: Database session
            gazetteer_name: Name of the gazetteer
            name: Name string to search for
            limit: Maximum number of results to return (default: 1000)
            ranks: Number of rank groups to include in results (default: 1)

        Returns:
            List of features that have names fuzzy matching this text, ordered by relevance (highest rank first)
        """
        # Trigram tokenization requires at least 3 characters
        if len(name) < 3:
            return []

        query = " OR ".join([f'"{name[i:i+3]}"' for i in range(len(name) - 2)])

        statement = (
            select(Feature, literal_column("bm25(name_fts_trigrams)").label("rank"))
            .join(Name, Feature.id == Name.feature_id)
            .join(NameFTSTrigrams, Name.id == NameFTSTrigrams.rowid)
            .where(
                Feature.gazetteer_name == gazetteer_name,
                NameFTSTrigrams.text.match(query),
            )
            .order_by(literal_column("bm25(name_fts_trigrams)"))
            .limit(limit)
        )
        results = db.exec(statement).unique().all()

        return cls._filter_by_ranks(results, ranks)

    @classmethod
    def _filter_by_ranks(cls, results: t.List[t.Tuple], ranks: int) -> t.List[Feature]:
        """
        Helper method to filter ranked results by top rank groups.

        Args:
            results: List of tuples where each tuple contains (Feature, rank)
            ranks: Number of rank groups to include in results

        Returns:
            List of Feature objects from the top N rank groups
        """
        if not results or ranks <= 0:
            return []

        # Get unique rank values and take only the top N rank groups
        unique_ranks = sorted(list(set(result[1] for result in results)))[:ranks]

        # Filter results to only include features from the top N rank groups
        filtered_results = [
            result[0] for result in results if result[1] in unique_ranks
        ]
        return filtered_results
