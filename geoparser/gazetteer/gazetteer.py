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

    def search(
        self, toponym: str, method: str = "exact", limit: int = 1000, ranks: int = 1
    ) -> List[Feature]:
        """
        Search for features using the specified search method.

        Args:
            toponym: Toponym string to search for
            method: Search method to use ("exact", "phrase", "substring", "permuted", "partial", "fuzzy")
            limit: Maximum number of results to return (default: 1000)
            ranks: Number of rank groups to include in results (default: 1, ignored for exact method)

        Returns:
            List of Feature objects matching the search criteria

        Raises:
            ValueError: If an unknown search method is specified
        """
        # Remove quotes and trim whitespace
        normalized_toponym = re.sub(r'"', "", toponym).strip()

        # Map method names to repository functions
        method_map = {
            "exact": lambda db: FeatureRepository.get_by_gazetteer_and_toponym_exact(
                db, self.gazetteer_name, normalized_toponym, limit
            ),
            "phrase": lambda db: FeatureRepository.get_by_gazetteer_and_toponym_phrase(
                db, self.gazetteer_name, normalized_toponym, limit, ranks
            ),
            "permuted": lambda db: FeatureRepository.get_by_gazetteer_and_toponym_permuted(
                db, self.gazetteer_name, normalized_toponym, limit, ranks
            ),
            "partial": lambda db: FeatureRepository.get_by_gazetteer_and_toponym_partial(
                db, self.gazetteer_name, normalized_toponym, limit, ranks
            ),
            "substring": lambda db: FeatureRepository.get_by_gazetteer_and_toponym_substring(
                db, self.gazetteer_name, normalized_toponym, limit, ranks
            ),
            "fuzzy": lambda db: FeatureRepository.get_by_gazetteer_and_toponym_fuzzy(
                db, self.gazetteer_name, normalized_toponym, limit, ranks
            ),
        }

        if method not in method_map:
            raise ValueError(f"Unknown search method: {method}")

        with Session(engine) as db:
            return method_map[method](db)

    def find(self, identifier: str) -> Feature | None:
        """
        Find a feature by its identifier.

        Args:
            identifier: The identifier value of the feature to find

        Returns:
            Feature object if found, None otherwise
        """
        with Session(engine) as db:
            return FeatureRepository.get_by_gazetteer_and_identifier(
                db, self.gazetteer_name, identifier
            )
