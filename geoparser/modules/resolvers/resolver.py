import typing as t
from abc import abstractmethod

from geoparser.modules.module import Module


class Resolver(Module):
    """
    Abstract class for modules that perform reference resolution.

    These modules link recognized references to specific referents in a gazetteer.
    Resolution modules focus solely on the prediction logic without database interactions.
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
    def predict_referents(
        self, reference_data: t.List[dict]
    ) -> t.List[t.List[t.Tuple[str, str]]]:
        """
        Predict referents for multiple references.

        This abstract method must be implemented by child classes.

        Args:
            reference_data: List of dictionaries containing reference information:
                          - start: start position in document
                          - end: end position in document
                          - text: the actual reference text
                          - document_text: full document text

        Returns:
            List of lists of tuples containing (gazetteer_name, identifier).
            Each inner list corresponds to referents found for one reference at the same index in the input list.
            The gazetteer_name identifies which gazetteer the identifier refers to,
            and the identifier is the value used to identify the referent in that gazetteer.
        """
