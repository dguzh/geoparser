import typing as t
from abc import ABC, abstractmethod
from uuid import UUID

from sqlmodel import Session, select

from geoparser.db.db import get_db


class BaseModule(ABC):
    """
    Abstract base class for any GeoparserV2 module.

    All modules must implement this interface to be compatible
    with the GeoparserV2 architecture.
    """

    def __init__(self, name: str):
        """
        Initialize a module.

        Args:
            name: A unique name for this module
        """
        self.name = name

    @abstractmethod
    def run(self, session_id: UUID) -> None:
        """
        Execute the module's functionality on the specified session.

        The module should read and write to the database as needed.

        Args:
            session_id: UUID of the session to process
        """
        pass


class RecognitionModule(BaseModule):
    """
    Abstract class for modules that perform toponym recognition.

    These modules identify potential toponyms in text and save them to the database.
    Recognition modules process documents and create toponym entries.
    """

    @abstractmethod
    def run(self, session_id: UUID) -> None:
        """
        Execute toponym recognition on documents in the specified session.

        This implementation should scan documents that haven't been processed
        by this recognition module yet and add new toponyms to the database.

        Args:
            session_id: UUID of the session to process
        """
        pass


class ResolutionModule(BaseModule):
    """
    Abstract class for modules that perform toponym resolution.

    These modules link recognized toponyms to specific locations in a gazetteer.
    Resolution modules process toponyms (regardless of which recognition module
    created them) and create location entries.
    """

    @abstractmethod
    def run(self, session_id: UUID) -> None:
        """
        Execute toponym resolution on toponyms in the specified session.

        This implementation should find toponyms that haven't been processed
        by this resolution module yet and resolve them to locations.

        Args:
            session_id: UUID of the session to process
        """
        pass
