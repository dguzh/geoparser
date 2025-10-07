import typing as t
from typing import List, Tuple

from geoparser.modules.resolvers import Resolver

if t.TYPE_CHECKING:
    pass


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

    def __init__(self, label: str, referents: List[List[Tuple[str, str]]]):
        """
        Initialize the ManualResolver with a label and referent annotations.

        Args:
            label: Identifier for this annotation set (e.g., "annotator_A", "expert_1").
                   Different labels create separate resolver instances in the database.
            referents: List of lists of (gazetteer_name, identifier) tuples representing the
                      resolved referents. Each inner list corresponds to referents for one
                      document's references. Must match the order and structure of documents
                      and references passed to run().
        """
        # Only label goes to config and database
        super().__init__(label=label)

        # Store as instance attributes
        self.label = label
        self.referents = referents

    def predict_referents(
        self, texts: t.List[str], references: t.List[t.List[t.Tuple[int, int]]]
    ) -> t.List[t.List[t.Tuple[str, str]]]:
        """
        Return the manually provided referent annotations for the given references.

        This method validates that the structure of references matches the structure of
        stored referent annotations and returns the annotations in the same order.

        Args:
            texts: List of document text strings
            references: List of lists of (start, end) position tuples

        Returns:
            List of lists of (gazetteer_name, identifier) tuples representing the
            resolved referents. Each inner list corresponds to referents for one document.

        Raises:
            ValueError: If the structure of references doesn't match the structure of
                       referent annotations
        """
        # Validate that the nested structure matches
        if len(references) != len(self.referents):
            raise ValueError(
                f"Number of documents ({len(references)}) does not match "
                f"number of document referent annotations ({len(self.referents)}). "
                f"Ensure annotations are provided for all documents in the same order."
            )

        for i, (doc_refs, doc_referents) in enumerate(zip(references, self.referents)):
            if len(doc_refs) != len(doc_referents):
                raise ValueError(
                    f"Number of references in document {i} ({len(doc_refs)}) does not match "
                    f"number of referent annotations ({len(doc_referents)}). "
                    f"Ensure annotations match the structure of references."
                )

        return self.referents
