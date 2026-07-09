"""
Runtime representation of a gazetteer feature.

Features are plain Python objects backed by a gazetteer artifact (a
self-contained SQLite file). They are not ORM models: attributes are stored as
a JSON object and geometry as WKB, both read directly from the artifact.
"""

from __future__ import annotations

import json
import typing as t
from functools import cached_property

from shapely import wkb
from shapely.geometry.base import BaseGeometry

if t.TYPE_CHECKING:
    from geoparser.gazetteer.artifact import GazetteerArtifact


class Feature:
    """
    A geographic feature from an installed gazetteer.

    Each feature has a stable identifier within its gazetteer, an entity type,
    a set of attributes (arbitrary per entity type), an optional geometry and
    one or more searchable names.
    """

    def __init__(
        self,
        artifact: "GazetteerArtifact",
        id: int,
        identifier: str,
        type: str,
        attributes: str,
        geometry: t.Optional[bytes],
    ):
        """
        Initialize a feature from an artifact row.

        Args:
            artifact: The artifact this feature belongs to
            id: Internal feature id within the artifact
            identifier: Stable identifier within the gazetteer
            type: Entity type (e.g. "city", "country")
            attributes: JSON-encoded attributes object
            geometry: WKB-encoded geometry, or None
        """
        self._artifact = artifact
        self.id = id
        self.identifier = identifier
        self.type = type
        self._attributes_json = attributes
        self._geometry_wkb = geometry

    @property
    def gazetteer_name(self) -> str:
        """Name of the gazetteer this feature belongs to."""
        return self._artifact.name

    @cached_property
    def data(self) -> t.Dict[str, t.Any]:
        """
        The feature's attributes as a dictionary.

        Returns:
            Dictionary of attribute names to values
        """
        return json.loads(self._attributes_json)

    @cached_property
    def geometry(self) -> t.Optional[BaseGeometry]:
        """
        The feature's geometry as a Shapely object.

        The geometry is stored in the gazetteer's coordinate reference system
        (available as ``Feature.crs``).

        Returns:
            Shapely geometry object, or None if the feature has no geometry
        """
        if self._geometry_wkb is None:
            return None
        return wkb.loads(bytes(self._geometry_wkb))

    @property
    def crs(self) -> str:
        """Coordinate reference system of the feature's geometry."""
        return self._artifact.crs

    @cached_property
    def names(self) -> t.List[str]:
        """
        All searchable names of this feature.

        Returns:
            List of name strings
        """
        return self._artifact.get_feature_names(self.id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Feature):
            return NotImplemented
        return (
            self.gazetteer_name == other.gazetteer_name
            and self.identifier == other.identifier
        )

    def __hash__(self) -> int:
        return hash((self.gazetteer_name, self.identifier))

    def __str__(self) -> str:
        """
        Return a string representation of the feature.

        Returns:
            String with feature indicator showing gazetteer and identifier
        """
        return f"Feature({self.gazetteer_name}:{self.identifier})"

    def __repr__(self) -> str:
        """
        Return a developer representation of the feature.

        Returns:
            Same as __str__ method
        """
        return self.__str__()
