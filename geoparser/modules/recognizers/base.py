import typing as t
from abc import abstractmethod

from geoparser.modules.module import Module


class Recognizer(Module):
    """
    Abstract class for modules that perform reference recognition.

    These modules identify potential references (place names) in text.
    They are completely database-agnostic and operate only on raw text data.
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
    def predict(
        self, texts: t.List[str]
    ) -> t.List[t.Union[t.List[t.Tuple[int, int]], None]]:
        """
        Predict references in multiple document texts.

        This abstract method must be implemented by child classes.

        Args:
            texts: List of document text strings to process

        Returns:
            List where each element is either:
            - A list of (start, end) tuples containing positions of references found in the document
            - None to indicate that predictions are not available for that document
              (e.g., unsupported language, missing data, etc.)
            Each element corresponds to one document at the same index in the input list.
        """
