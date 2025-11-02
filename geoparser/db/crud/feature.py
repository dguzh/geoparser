import typing as t

from sqlalchemy import func, literal_column
from sqlmodel import Session, select

from geoparser.db.crud.base import BaseRepository
from geoparser.db.models.feature import Feature
from geoparser.db.models.gazetteer import Gazetteer
from geoparser.db.models.name import Name, NameFTS, NameSpellfixVocab
from geoparser.db.models.source import Source


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
        statement = (
            select(Feature)
            .join(Source, Feature.source_id == Source.id)
            .join(Gazetteer, Source.gazetteer_id == Gazetteer.id)
            .where(Gazetteer.name == gazetteer_name)
        )
        return db.exec(statement).unique().all()

    @classmethod
    def get_by_gazetteer_and_identifier(
        cls, db: Session, gazetteer_name: str, location_id_value: str
    ) -> t.Optional[Feature]:
        """
        Get a feature by gazetteer name and identifier value.

        Args:
            db: Database session
            gazetteer_name: Name of the gazetteer
            location_id_value: Identifier value within that gazetteer

        Returns:
            Feature if found, None otherwise
        """
        statement = (
            select(Feature)
            .join(Source, Feature.source_id == Source.id)
            .join(Gazetteer, Source.gazetteer_id == Gazetteer.id)
            .where(
                Gazetteer.name == gazetteer_name,
                Feature.location_id_value == location_id_value,
            )
        )
        return db.exec(statement).unique().first()

    @classmethod
    def get_by_gazetteer_and_name_exact(
        cls, db: Session, gazetteer_name: str, name: str, limit: int = 10000
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
            limit: Maximum number of results to return (default: 10000)

        Returns:
            List of features that have this exact name
        """
        query = f'"{name}"'

        statement = (
            select(Feature)
            .join(Source, Feature.source_id == Source.id)
            .join(Gazetteer, Source.gazetteer_id == Gazetteer.id)
            .join(Name, Feature.id == Name.feature_id)
            .join(NameFTS, Name.id == NameFTS.rowid)
            .where(
                Gazetteer.name == gazetteer_name,
                NameFTS.text.match(query),
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
        limit: int = 10000,
        tiers: int = 1,
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
            limit: Maximum number of results to return (default: 10000)
            tiers: Number of rank tiers to include in results (default: 1)

        Returns:
            List of features that have names containing this text as a phrase, ordered by relevance (best score first)
        """
        query = f'"{name}"'

        score = literal_column("bm25(name_fts)")

        scored = (
            select(
                Feature.id.label("feature_id"),
                score.label("score"),
            )
            .join(Source, Feature.source_id == Source.id)
            .join(Gazetteer, Source.gazetteer_id == Gazetteer.id)
            .join(Name, Feature.id == Name.feature_id)
            .join(NameFTS, Name.id == NameFTS.rowid)
            .where(
                Gazetteer.name == gazetteer_name,
                NameFTS.text.match(query),
            )
            .order_by(score.asc())
            .limit(limit)
        ).cte("scored")

        tiered = (
            select(
                scored.c.feature_id,
                scored.c.score,
                func.dense_rank().over(order_by=scored.c.score.asc()).label("tier"),
            ).select_from(scored)
        ).cte("tiered")

        statement = (
            select(Feature)
            .join(tiered, Feature.id == tiered.c.feature_id)
            .where(tiered.c.tier <= tiers)
            .order_by(tiered.c.score.asc(), Feature.id.asc())
        )

        return db.exec(statement).unique().all()

    @classmethod
    def get_by_gazetteer_and_name_partial(
        cls,
        db: Session,
        gazetteer_name: str,
        name: str,
        limit: int = 10000,
        tiers: int = 1,
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
            limit: Maximum number of results to return (default: 10000)
            tiers: Number of rank tiers to include in results (default: 1)

        Returns:
            List of features that have names partially matching the search tokens, ordered by relevance (best score first)
        """
        query = " OR ".join(
            [f'"{token.strip()}"' for token in name.split() if token.strip()]
        )

        score = literal_column("bm25(name_fts)")

        scored = (
            select(
                Feature.id.label("feature_id"),
                score.label("score"),
            )
            .join(Source, Feature.source_id == Source.id)
            .join(Gazetteer, Source.gazetteer_id == Gazetteer.id)
            .join(Name, Feature.id == Name.feature_id)
            .join(NameFTS, Name.id == NameFTS.rowid)
            .where(
                Gazetteer.name == gazetteer_name,
                NameFTS.text.match(query),
            )
            .order_by(score.asc())
            .limit(limit)
        ).cte("scored")

        tiered = (
            select(
                scored.c.feature_id,
                scored.c.score,
                func.dense_rank().over(order_by=scored.c.score.asc()).label("tier"),
            ).select_from(scored)
        ).cte("tiered")

        statement = (
            select(Feature)
            .join(tiered, Feature.id == tiered.c.feature_id)
            .where(tiered.c.tier <= tiers)
            .order_by(tiered.c.score.asc(), Feature.id.asc())
        )

        return db.exec(statement).unique().all()

    @classmethod
    def get_by_gazetteer_and_name_fuzzy(
        cls,
        db: Session,
        gazetteer_name: str,
        name: str,
        limit: int = 10000,
        tiers: int = 1,
    ) -> t.List[Feature]:
        """
        Get all features for a gazetteer that have names fuzzy matching the search term.

        Uses the spellfix1 virtual table for fuzzy matching with phonetic hashing and edit distance.
        This method computes the phonetic hash (k2) of the query and finds candidates with the same
        k2 value, then groups results by edit distance. The tiers parameter controls how many
        distance tiers to include in the results.

        Args:
            db: Database session
            gazetteer_name: Name of the gazetteer
            name: Name string to search for
            limit: Maximum number of results to return (default: 10000)
            tiers: Number of rank tiers (edit distance levels) to include in results (default: 1)

        Returns:
            List of features that have names fuzzy matching this text, grouped by edit distance
        """
        score = func.min(
            func.editdist3(name, literal_column("name_spellfix_vocab.word"))
        )

        scored = (
            select(
                Feature.id.label("feature_id"),
                score.label("score"),
            )
            .join(Source, Feature.source_id == Source.id)
            .join(Gazetteer, Source.gazetteer_id == Gazetteer.id)
            .join(Name, Feature.id == Name.feature_id)
            .join(NameSpellfixVocab, Name.id == NameSpellfixVocab.id)
            .where(
                Gazetteer.name == gazetteer_name,
                NameSpellfixVocab.k2 == func.spellfix1_phonehash(name),
            )
            .group_by(Feature.id)
            .order_by(score.asc())
            .limit(limit)
        ).cte("scored")

        tiered = (
            select(
                scored.c.feature_id,
                scored.c.score,
                func.dense_rank().over(order_by=scored.c.score.asc()).label("tier"),
            ).select_from(scored)
        ).cte("tiered")

        statement = (
            select(Feature)
            .join(tiered, Feature.id == tiered.c.feature_id)
            .where(tiered.c.tier <= tiers)
            .order_by(tiered.c.score.asc(), Feature.id.asc())
        )

        return db.exec(statement).unique().all()
