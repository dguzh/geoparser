import typing as t
from typing import List, Tuple

from geoparser.modules.recognizers import Recognizer

if t.TYPE_CHECKING:
    from geoparser.db.models import Document


class ManualRecognizer(Recognizer):
    """
    A recognition module for manually annotated references.

    This module allows manual reference annotations to be integrated into the
    geoparsing workflow. Each instance is identified by a label, enabling
    multiple annotation sets (e.g., from different annotators) to be stored
    for the same documents.

    The annotations are provided at initialization and returned by predict_references()
    in the same order as the input documents. The label is stored in the database
    config to differentiate between different annotation sets.
    """

    NAME = "ManualRecognizer"

    def __init__(self, label: str, references: List[List[Tuple[int, int]]]):
        """
        Initialize the ManualRecognizer with a label and reference annotations.

        Args:
            label: Identifier for this annotation set (e.g., "annotator_A", "expert_1").
                   Different labels create separate recognizer instances in the database.
            references: List of reference annotations, where each element is a list of
                       (start, end) tuples representing reference spans in the corresponding
                       document. Must match the order and number of documents passed to run().
        """
        # Only label goes to config and database
        super().__init__(label=label)

        # Store as instance attributes
        self.label = label
        self.references = references

    def predict_references(
        self, documents: t.List["Document"]
    ) -> t.List[t.List[t.Tuple[int, int]]]:
        """
        Return the manually provided reference annotations for the given documents.

        This method validates that the number of documents matches the number of
        annotation sets and returns the annotations in the same order.

        Args:
            documents: List of Document ORM objects to annotate

        Returns:
            List of lists of (start, end) tuples representing reference spans.
            Each inner list corresponds to references for one document.

        Raises:
            ValueError: If the number of documents doesn't match the number of
                       reference annotation sets
        """
        if len(documents) != len(self.references):
            raise ValueError(
                f"Number of documents ({len(documents)}) does not match "
                f"number of reference annotations ({len(self.references)}). "
                f"Ensure annotations are provided for all documents in the same order."
            )

        return self.references
