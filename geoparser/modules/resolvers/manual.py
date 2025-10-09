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

    def __init__(
        self,
        label: str,
        texts: List[str],
        references: List[List[Tuple[int, int]]],
        referents: List[List[Tuple[str, str]]],
    ):
        """
        Initialize the ManualResolver with a label and referent annotations.

        Args:
            label: Identifier for this annotation set (e.g., "annotator_A", "expert_1").
                   Different labels create separate resolver instances in the database.
            texts: List of document text strings corresponding to the annotations.
            references: List of lists of (start, end) tuples representing reference positions.
                       Each inner list corresponds to references in one document.
            referents: List of lists of (gazetteer_name, identifier) tuples representing the
                      resolved referents. Each annotation corresponds to the document and
                      reference at the same positions in texts and references.
        """
        # Only label goes to config and database
        super().__init__(label=label)

        # Store as instance attributes
        self.label = label
        self.texts = texts
        self.references = references
        self.referents = referents

    def predict_referents(
        self, texts: t.List[str], references: t.List[t.List[t.Tuple[int, int]]]
    ) -> t.List[t.List[t.Union[t.Tuple[str, str], None]]]:
        """
        Return the manually provided referent annotations for the given references.

        This method matches each input text to the corresponding annotation by looking
        up the text in the stored texts list, then matches each reference within that
        document to find the corresponding referent annotation. For references without
        annotations, None is returned.

        Args:
            texts: List of document text strings
            references: List of lists of (start, end) position tuples

        Returns:
            List of lists where each element is either:
            - A tuple (gazetteer_name, identifier) for annotated references
            - None for references without annotations (which won't be marked as processed)
        """
        results = []
        for text, doc_references in zip(texts, references):
            try:
                text_idx = self.texts.index(text)
                stored_references = self.references[text_idx]
                stored_referents = self.referents[text_idx]

                doc_results = []
                for reference in doc_references:
                    try:
                        reference_idx = stored_references.index(reference)
                        doc_results.append(stored_referents[reference_idx])
                    except ValueError:
                        # Reference not in stored annotations - return None
                        # This signals to the service that no annotation is available
                        doc_results.append(None)

                results.append(doc_results)
            except ValueError:
                # Text not in stored annotations - return None for all references in this document
                results.append([None] * len(doc_references))

        return results
