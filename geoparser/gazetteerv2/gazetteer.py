from typing import List

from sqlmodel import Session

from geoparser.db.crud.feature import FeatureRepository
from geoparser.db.db import engine
from geoparser.db.models.feature import Feature


class Gazetteer:
    """
    A gazetteer interface for querying geographic features.

    This class provides access to gazetteer data stored in the local database,
    allowing retrieval of candidate features for toponym matching.
    """

    def __init__(self, gazetteer_name: str):
        """
        Initialize the gazetteer interface.

        Args:
            gazetteer_name: Name of the gazetteer to query for candidates
        """
        self.gazetteer_name = gazetteer_name

    def get_candidates(self, toponyms: List[str]) -> List[List[Feature]]:
        """
        Retrieve candidate features by exact toponym matching.

        Args:
            toponyms: List of toponym strings to find exact matches for

        Returns:
            List of lists of Feature objects. Each inner list contains
            all features that have an exactly matching toponym in the gazetteer.
        """
        with Session(engine) as db:
            results = []

            for toponym in toponyms:
                # Use the FeatureRepository to get features with exact toponym match
                features = FeatureRepository.get_by_gazetteer_and_toponym(
                    db, self.gazetteer_name, toponym
                )
                results.append(features)

            return results
