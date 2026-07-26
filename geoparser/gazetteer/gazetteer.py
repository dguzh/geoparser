"""
Public gazetteer query interface.

A Gazetteer wraps an installed artifact (a self-contained, read-only SQLite
file) and exposes name search and identifier lookup over its features.
"""

from __future__ import annotations

import re
from typing import List, Optional

from geoparser.gazetteer.artifact import GazetteerArtifact, artifact_path
from geoparser.gazetteer.feature import Feature


class Gazetteer:
    """
    A gazetteer interface for querying geographic features.

    This class provides access to an installed gazetteer artifact, allowing
    retrieval of candidate features for name matching using different search
    strategies: exact, phrase, partial, and fuzzy matching.
    """

    def __init__(self, gazetteer_name: str):
        """
        Initialize the gazetteer interface.

        Args:
            gazetteer_name: Name of the gazetteer to query for candidates

        Raises:
            ValueError: If the gazetteer is not installed. Querying an
                uninstalled gazetteer would silently return no results, so we
                fail here instead of letting that happen unnoticed.
        """
        path = artifact_path(gazetteer_name)
        if not path.exists():
            raise ValueError(f"Gazetteer '{gazetteer_name}' is not installed.")
        self.gazetteer_name = gazetteer_name
        self._artifact = GazetteerArtifact(path)

    @property
    def crs(self) -> str:
        """Coordinate reference system of the gazetteer's geometries."""
        return self._artifact.crs

    def search(
        self, name: str, method: str = "exact", limit: int = 10000, tiers: int = 1
    ) -> List[Feature]:
        """
        Search for features using the specified search method.

        Args:
            name: Name string to search for
            method: Search method to use ("exact", "phrase", "partial", "fuzzy")
            limit: Maximum number of results to return (default: 10000)
            tiers: Number of rank tiers to include in results (default: 1,
                ignored for exact method)

        Returns:
            List of Feature objects matching the search criteria

        Raises:
            ValueError: If an unknown search method is specified
        """
        # Remove quotes and trim whitespace
        normalized_name = re.sub(r'"', "", name).strip()
        if not normalized_name:
            return []

        method_map = {
            "exact": lambda: self._artifact.search_exact(normalized_name, limit),
            "phrase": lambda: self._artifact.search_phrase(
                normalized_name, limit, tiers
            ),
            "partial": lambda: self._artifact.search_partial(
                normalized_name, limit, tiers
            ),
            "fuzzy": lambda: self._artifact.search_fuzzy(normalized_name, limit, tiers),
        }

        if method not in method_map:
            raise ValueError(f"Unknown search method: {method}")

        return method_map[method]()

    def find(self, identifier: str) -> Optional[Feature]:
        """
        Find a feature by its identifier.

        Args:
            identifier: The identifier value of the feature to find

        Returns:
            Feature object if found, None otherwise
        """
        return self._artifact.find(identifier)
