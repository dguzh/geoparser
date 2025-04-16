import typing as t
from abc import ABC, abstractmethod


class AbstractModule(ABC):
    """
    Abstract base class for any geoparser module.

    All modules must implement this interface to be compatible
    with the geoparser architecture.

    Modules focus purely on the prediction logic without database interactions.
    """

    # Module name should be defined by subclasses
    NAME: str = None

    def __init__(self, **kwargs):
        """
        Initialize a module.

        Args:
            **kwargs: Configuration parameters for this module
        """
        if self.NAME is None:
            raise ValueError("Module must define a NAME class attribute")

        self.name = self.NAME
        self.config = self._initialize_config(kwargs)

    def _initialize_config(self, kwargs_dict: dict) -> dict:
        """
        Initialize configuration dictionary for consistent storage.

        This helper method:
        1. Converts sets to lists for JSON serialization
        2. Sorts items by key for order-invariant config distinction

        Args:
            kwargs_dict: Raw configuration dictionary

        Returns:
            Normalized configuration dictionary
        """
        # Process each value: convert sets to sorted lists
        config_dict = {}
        for key, value in kwargs_dict.items():
            if isinstance(value, set):
                config_dict[key] = sorted(list(value))
            else:
                config_dict[key] = value

        # Sort by key for consistent ordering
        sorted_items = sorted(config_dict.items(), key=lambda x: x[0])
        return dict(sorted_items)

    def __str__(self) -> str:
        """
        Return a string representation of the module.

        Returns:
            String with module name and config parameters
        """
        config_str = ", ".join(f"{k}={repr(v)}" for k, v in self.config.items())
        return f"{self.name}({config_str})"

    def __repr__(self) -> str:
        """
        Return a developer representation of the module.

        Returns:
            Same as __str__ method
        """
        return self.__str__()


class AbstractRecognitionModule(AbstractModule):
    """
    Abstract class for modules that perform toponym recognition.

    These modules identify potential toponyms in text.
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


class AbstractResolutionModule(AbstractModule):
    """
    Abstract class for modules that perform toponym resolution.

    These modules link recognized toponyms to specific locations in a gazetteer.
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
                          - text: the actual toponym text
                          - document_text: full document text

        Returns:
            List of lists of tuples containing (location_id, confidence).
            Each inner list corresponds to locations found for one toponym at the same index in the input list.
        """
