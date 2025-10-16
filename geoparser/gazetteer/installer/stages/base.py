from abc import ABC, abstractmethod
from typing import Any, Dict

from geoparser.gazetteer.installer.model import SourceConfig


class Stage(ABC):
    """
    Abstract base class for pipeline stages.

    Each stage represents a distinct phase in the gazetteer installation
    process. Stages are executed sequentially and should have a single,
    well-defined responsibility.

    Attributes:
        name: Human-readable name for this stage
        description: Brief description of what this stage does
    """

    def __init__(self, name: str, description: str):
        """
        Initialize a pipeline stage.

        Args:
            name: Human-readable name for this stage
            description: Brief description of what this stage does
        """
        self.name = name
        self.description = description

    @abstractmethod
    def execute(self, source: SourceConfig, context: Dict[str, Any]) -> None:
        """
        Execute this stage for a given source.

        Args:
            source: Source configuration to process
            context: Shared context dictionary containing information from
                previous stages (e.g., file paths, table names)

        Raises:
            Exception: If the stage execution fails
        """

    def __str__(self) -> str:
        """Return a string representation of this stage."""
        return f"{self.name}: {self.description}"

    def __repr__(self) -> str:
        """Return a developer representation of this stage."""
        return f"{self.__class__.__name__}(name='{self.name}')"
