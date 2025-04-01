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

        self.config = config or {}

        # Include the module name in the config to ensure uniqueness
        self.config["module_name"] = self.NAME

    def get_config_string(self) -> str:
        """
        Get a string representation of the module's configuration.

        This can be used for logging and debugging purposes.

        Returns:
            String representation of the config
        """
        if not self.config or len(self.config) <= 1:  # Only module_name key
            return "no config"

        config_items = []
        for key, value in self.config.items():
            if key == "module_name":
                continue  # Skip the module name in the string representation

            if isinstance(value, str) and len(value) > 20:
                # Truncate long string values
                value_str = f"{value[:17]}..."
            else:
                value_str = str(value)
            config_items.append(f"{key}={value_str}")

        return ", ".join(config_items)


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
