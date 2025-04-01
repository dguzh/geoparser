import hashlib
import json
import typing as t
from abc import ABC, abstractmethod


class BaseModule(ABC):
    """
    Abstract base class for any GeoparserProject module.

    All modules must implement this interface to be compatible
    with the GeoparserProject architecture.

    Modules focus purely on the prediction logic without database interactions.
    """

    # Module name should be defined by subclasses
    NAME: str = None

    def __init__(self, config: t.Optional[dict] = None):
        """
        Initialize a module.

        Args:
            config: Optional configuration parameters for this module
        """
        if self.NAME is None:
            raise ValueError("Module must define a NAME class attribute")

        self.name = self.NAME
        self.config = config or {}

    def __str__(self) -> str:
        """
        Get a string representation of the module.

        Returns:
            Short string with module name and config hash
        """
        config_str = json.dumps(self.config, sort_keys=True)
        config_hash = hashlib.md5(config_str.encode("utf-8")).hexdigest()[:8]
        return f"<{self.name} (config={config_hash})>"


class RecognitionModule(BaseModule):
    """
    Abstract class for modules that perform toponym recognition.

    These modules identify potential toponyms in text.
    Recognition modules focus solely on the prediction logic without database interactions.
    """

    # This base class should have NAME set to None since it should not be instantiated directly
    NAME = None

    def __init__(self, config: t.Optional[dict] = None):
        """
        Initialize a recognition module.

        Args:
            config: Optional configuration parameters for this module
        """
        super().__init__(config)

    @abstractmethod
    def predict_toponyms(
        self, document_texts: t.List[str]
    ) -> t.List[t.List[t.Tuple[int, int]]]:
        """
        Predict toponyms in multiple documents.

        This abstract method must be implemented by child classes.

        Args:
            document_texts: List of document texts to process

        Returns:
            List of lists of tuples containing (start, end) positions of toponyms.
            Each inner list corresponds to toponyms found in one document at the same index in the input list.
        """


class ResolutionModule(BaseModule):
    """
    Abstract class for modules that perform toponym resolution.

    These modules link recognized toponyms to specific locations in a gazetteer.
    Resolution modules focus solely on the prediction logic without database interactions.
    """

    # This base class should have NAME set to None since it should not be instantiated directly
    NAME = None

    def __init__(self, config: t.Optional[dict] = None):
        """
        Initialize a resolution module.

        Args:
            config: Optional configuration parameters for this module
        """
        super().__init__(config)

    @abstractmethod
    def predict_locations(
        self, toponym_data: t.List[dict]
    ) -> t.List[t.List[t.Tuple[str, t.Optional[float]]]]:
        """
        Predict locations for multiple toponyms.

        This abstract method must be implemented by child classes.

        Args:
            toponym_data: List of dictionaries containing toponym information:
                          - start: start position in document
                          - end: end position in document
                          - document_text: full document text

        Returns:
            List of lists of tuples containing (location_id, confidence).
            Each inner list corresponds to locations found for one toponym at the same index in the input list.
        """
