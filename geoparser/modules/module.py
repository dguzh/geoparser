import hashlib
import json
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
        # Normalize config using JSON round-trip to ensure consistent serialization
        self.config = json.loads(json.dumps(kwargs, sort_keys=True))

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

    @property
    def id(self) -> str:
        """
        Generate a deterministic ID for this module based on name and config.

        This ID is computed by hashing the module's string representation,
        ensuring that modules with the same name and config get the same ID,
        while modules with different configs get unique IDs.

        Returns:
            String ID uniquely identifying this module configuration
        """
        # Hash the string representation to create a short, deterministic ID
        hash_object = hashlib.sha256(str(self).encode())
        # Use first 8 characters of hex digest for a reasonably short ID
        return hash_object.hexdigest()[:8]
