import typing as t
from abc import abstractmethod

from geoparser.modules.module import Module


class Resolver(Module):
    """
    Abstract class for modules that perform reference resolution.

    These modules link recognized references to specific referents in a gazetteer.
    They are completely database-agnostic and operate only on raw text data.
    """

    # This base class should have NAME set to None since it should not be instantiated directly
    NAME = None

    def __init__(self, **kwargs):
        """
        Initialize a resolution module.

        Args:
            **kwargs: Configuration parameters for this module
        """
        super().__init__(**kwargs)

    @abstractmethod
    def predict(
        self, texts: t.List[str], references: t.List[t.List[t.Tuple[int, int]]]
    ) -> t.List[t.List[t.Union[t.Tuple[str, str], None]]]:
        """
        Predict referents for multiple references across multiple documents.

        This abstract method must be implemented by child classes.

        Args:
            texts: List of document text strings
            references: List of lists of tuples containing (start, end) positions of references.
                       Each inner list corresponds to references in one document at the same index in texts.

        Returns:
            List of lists where each element is either:
            - A tuple (gazetteer_name, identifier) for a successfully resolved reference
            - None to indicate that prediction is not available for that specific reference
              (e.g., missing data, unsupported format, etc.)
            Each inner list corresponds to referents for references in one document.
            Each element at position [i][j] is the referent (or None) for the reference at position [i][j] in the input.
            The gazetteer_name identifies which gazetteer the identifier refers to,
            and the identifier is the value used to identify the referent in that gazetteer.
        """
