import typing as t
from abc import abstractmethod

from geoparser.modules.module import Module


class Recognizer(Module):
    """
    Abstract class for modules that perform reference recognition.

    These modules identify potential references (place names) in text.
    Recognition modules focus solely on the prediction logic without database interactions.
    """

    # This base class should have NAME set to None since it should not be instantiated directly
    NAME = None

    def __init__(self, **kwargs):
        """
        Initialize a recognition module.

        Args:
            **kwargs: Configuration parameters for this module
        """
        super().__init__(**kwargs)

    @abstractmethod
    def predict_references(
        self, document_texts: t.List[str]
    ) -> t.List[t.List[t.Tuple[int, int]]]:
        """
        Predict references in multiple documents.

        This abstract method must be implemented by child classes.

        Args:
            document_texts: List of document texts to process

        Returns:
            List of lists of tuples containing (start, end) positions of references.
            Each inner list corresponds to references found in one document at the same index in the input list.
        """
