from abc import ABC


class Module(ABC):
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
