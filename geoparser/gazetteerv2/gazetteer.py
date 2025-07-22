import re
from typing import List

from sqlmodel import Session

from geoparser.db.crud.feature import FeatureRepository
from geoparser.db.db import engine
from geoparser.db.models.feature import Feature


class Gazetteer:
    """
    A gazetteer interface for querying geographic features.

    This class provides access to gazetteer data stored in the local database,
    allowing retrieval of candidate features for toponym matching using different
    search strategies: exact, partial, and fuzzy matching.
    """

    def __init__(self, gazetteer_name: str):
        """
        Initialize the gazetteer interface.

        Args:
            gazetteer_name: Name of the gazetteer to query for candidates
        """
        self.gazetteer_name = gazetteer_name

    def search_exact(self, toponym: str, limit: int = 1000) -> List[Feature]:
        """
        Search for features with exactly matching toponyms.

        Only returns features where the toponym text has exactly the same length
        as the search query and matches case-insensitively.

        Args:
            toponym: Toponym string to search for
            limit: Maximum number of results to return (default: 1000)

        Returns:
            List of Feature objects that have this exact toponym
        """
        # Remove quotes and trim whitespace
        normalized_toponym = re.sub(r'"', "", toponym).strip()

        with Session(engine) as db:
            return FeatureRepository.get_by_gazetteer_and_toponym_exact(
                db, self.gazetteer_name, normalized_toponym, limit
            )

    def search_partial(
        self, toponym: str, limit: int = 1000, ranks: int = 1
    ) -> List[Feature]:
        """
        Search for features with toponyms containing the search term.

        Returns features where the toponym text contains the search query as a substring,
        using BM25 ranking for relevance scoring.

        Args:
            toponym: Toponym string to search for
            limit: Maximum number of results to return (default: 1000)
            ranks: Number of rank groups to include in results (default: 1)

        Returns:
            List of Feature objects that have toponyms containing this text,
            ordered by relevance (highest rank first)
        """
        # Remove quotes and trim whitespace
        normalized_toponym = re.sub(r'"', "", toponym).strip()

        with Session(engine) as db:
            return FeatureRepository.get_by_gazetteer_and_toponym_partial(
                db, self.gazetteer_name, normalized_toponym, limit, ranks
            )

    def search_fuzzy(
        self, toponym: str, limit: int = 1000, ranks: int = 1
    ) -> List[Feature]:
        """
        Search for features with toponyms fuzzy matching the search term.

        Uses trigram-based fuzzy matching for approximate string matching,
        allowing for typos and partial character matches with BM25 ranking.

        Args:
            toponym: Toponym string to search for
            limit: Maximum number of results to return (default: 1000)
            ranks: Number of rank groups to include in results (default: 1)

        Returns:
            List of Feature objects that have toponyms fuzzy matching this text,
            ordered by relevance (highest rank first)
        """
        # Remove quotes and trim whitespace
        normalized_toponym = re.sub(r'"', "", toponym).strip()

        with Session(engine) as db:
            return FeatureRepository.get_by_gazetteer_and_toponym_fuzzy(
                db, self.gazetteer_name, normalized_toponym, limit, ranks
            )
