import typing as t
import uuid

from sqlmodel import Session, select

from geoparser.db.db import get_db
from geoparser.db.models import Document, DocumentCreate, SessionCreate
from geoparser.geoparserv2.modules import BaseModule


class GeoparserV2:
    """
    Main entry point for the GeoparserV2 module.

    This class provides a unified interface for geoparsing operations
    including document management, toponym recognition, and resolution.
    """

    def __init__(self, session: str):
        """
        Initialize a GeoparserV2 instance.

        Args:
            session: Session name. Will load or create a session with this name.
        """
        self.session_name = session
        self._load_or_create_session(session)

    def _load_or_create_session(self, session_name: str):
        """Load an existing session or create a new one if it doesn't exist."""
        # Implementation for loading or creating a session
        pass

    def add_document(self, text: str) -> uuid.UUID:
        """
        Add a new document to the session.

        Args:
            text: The text content of the document.

        Returns:
            UUID of the created document.
        """
        # Implementation for adding a document
        pass

    def run(self, module: BaseModule) -> None:
        """
        Run a processing module on the current session.

        This method will execute the specified module, which can be either
        a recognition module or a resolution module.

        Args:
            module: The module instance to run.
        """
        # Implementation for running a module
        module.run(self.session_id)

    def get_documents(self) -> list[dict]:
        """
        Retrieve all documents in the current session.

        Returns:
            List of document dictionaries with id and text.
        """
        # Implementation for retrieving documents
        pass

    def get_toponyms(self, recognition_module_name: str) -> list[dict]:
        """
        Get toponyms recognized by a specific recognition module.

        Args:
            recognition_module_name: Name of the recognition module.

        Returns:
            List of toponym dictionaries with relevant information.
        """
        # Implementation for retrieving toponyms
        pass

    def get_locations(
        self, recognition_module_name: str, resolution_module_name: str
    ) -> list[dict]:
        """
        Get locations resolved by a specific combination of recognition and resolution modules.

        Args:
            recognition_module_name: Name of the recognition module that produced the toponyms.
            resolution_module_name: Name of the resolution module that resolved the locations.

        Returns:
            List of location dictionaries with relevant information.
        """
        # Implementation for retrieving locations
        pass
