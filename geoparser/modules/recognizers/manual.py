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

    def predict(
        self, texts: t.List[str]
    ) -> t.List[t.Union[t.List[t.Tuple[int, int]], None]]:
        """
        Return the manually provided reference annotations for the given documents.

        This method matches each input text to the corresponding annotation by looking
        up the text in the stored texts list. For texts that don't have annotations,
        None is returned to indicate that no annotation is available (as opposed to
        an empty list which would indicate that the document was annotated as having
        no references).

        Args:
            texts: List of document text strings to annotate

        Returns:
            A list where each element is either a list of (start, end) tuples representing
            reference spans for annotated documents, or None for documents without annotations
            (which won't be marked as processed).
        """
        results = []
        for text in texts:
            try:
                idx = self.texts.index(text)
                results.append(self.references[idx])
            except ValueError:
                # Text not in stored annotations - return None
                # This signals to the service that no annotation is available
                results.append(None)

        return results
