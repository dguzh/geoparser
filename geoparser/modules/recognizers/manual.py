import typing as t
from typing import List, Tuple

from geoparser.modules.recognizers import Recognizer

if t.TYPE_CHECKING:
    pass


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

    def __init__(
        self, label: str, texts: List[str], references: List[List[Tuple[int, int]]]
    ):
        """
        Initialize the ManualRecognizer with a label and reference annotations.

        Args:
            label: Identifier for this annotation set (e.g., "annotator_A", "expert_1").
                   Different labels create separate recognizer instances in the database.
            texts: List of document text strings corresponding to the annotations.
            references: List of reference annotations, where each element is a list of
                       (start, end) tuples representing reference spans. Each annotation
                       set corresponds to the document text at the same position in texts.
        """
        # Only label goes to config and database
        super().__init__(label=label)

        # Store as instance attributes
        self.label = label
        self.texts = texts
        self.references = references

    def predict_references(
        self, texts: t.List[str]
    ) -> t.List[t.List[t.Tuple[int, int]]]:
        """
        Return the manually provided reference annotations for the given documents.

        This method matches each input text to the corresponding annotation by looking
        up the text in the stored texts list. Only texts that have annotations will
        be processed, and the order is determined by the input texts, not the stored
        annotations.

        Args:
            texts: List of document text strings to annotate

        Returns:
            List of lists of (start, end) tuples representing reference spans.
            Each inner list corresponds to references for one document.
        """
        results = []
        for text in texts:
            idx = self.texts.index(text)
            results.append(self.references[idx])

        return results
