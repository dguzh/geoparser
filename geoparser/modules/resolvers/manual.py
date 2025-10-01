import typing as t
from typing import List, Tuple

from geoparser.modules.resolvers import Resolver

if t.TYPE_CHECKING:
    from geoparser.db.models import Reference


class ManualResolver(Resolver):
    """
    A resolution module for manually annotated referents.

    This module allows manual referent annotations (links to gazetteer features)
    to be integrated into the geoparsing workflow. Each instance is identified by
    a label, enabling multiple annotation sets (e.g., from different annotators)
    to be stored for the same references.

    The annotations are provided at initialization and returned by predict_referents()
    in the same order as the input references. The label is stored in the database
    config to differentiate between different annotation sets.
    """

    NAME = "ManualResolver"

    def __init__(self, label: str, referents: List[Tuple[str, str]]):
        """
        Initialize the ManualResolver with a label and referent annotations.

        Args:
            label: Identifier for this annotation set (e.g., "annotator_A", "expert_1").
                   Different labels create separate resolver instances in the database.
            referents: List of (gazetteer_name, identifier) tuples representing the
                      resolved referents for each reference. Must match the order and
                      number of references passed to run().
        """
        # Only label goes to config and database
        super().__init__(label=label)

        # Store as instance attributes
        self.label = label
        self.referents = referents

    def predict_referents(
        self, references: t.List["Reference"]
    ) -> t.List[t.Tuple[str, str]]:
        """
        Return the manually provided referent annotations for the given references.

        This method validates that the number of references matches the number of
        referent annotations and returns the annotations in the same order.

        Args:
            references: List of Reference ORM objects to resolve

        Returns:
            List of (gazetteer_name, identifier) tuples representing the resolved
            referents. Each tuple corresponds to one reference.

        Raises:
            ValueError: If the number of references doesn't match the number of
                       referent annotations
        """
        if len(references) != len(self.referents):
            raise ValueError(
                f"Number of references ({len(references)}) does not match "
                f"number of referent annotations ({len(self.referents)}). "
                f"Ensure annotations are provided for all references in the same order."
            )

        return self.referents
