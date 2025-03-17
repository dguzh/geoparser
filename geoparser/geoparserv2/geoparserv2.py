import uuid
import typing as t
import logging

from sqlmodel import Session as DBSession

from geoparser.db.crud import SessionRepository
from geoparser.db.db import get_db
from geoparser.db.models import Session, SessionCreate
from geoparser.geoparserv2.modules import BaseModule


class GeoparserV2:
    """
    Main entry point for the GeoparserV2 module.

    This class provides a unified interface for geoparsing operations
    including document management, toponym recognition, and resolution.
    """

    def __init__(self, session_name: str):
        """
        Initialize a GeoparserV2 instance.

        Args:
            session: Session name. Will load or create a session with this name.
        """
        self.session = self._load_or_create_session(session_name)

    def _load_or_create_session(self, session_name: str) -> Session:
        """
        Load an existing session or create a new one if it doesn't exist.
        
        Args:
            session_name: Name of the session to load or create
            
        Returns:
            Session object that was loaded or created
        """
        db = next(get_db())
        session = self.load_session(db, session_name)
        
        if session is None:
            logging.info(f"No session found with name '{session_name}'; creating a new one.")
            session = self.create_session(db, session_name)
            
        return session
        
    def load_session(self, db: DBSession, session_name: str) -> t.Optional[Session]:
        """
        Load a session by name from the database.
        
        Args:
            db: Database session
            session_name: Name of the session to load
            
        Returns:
            Session if found, None otherwise
        """
        return SessionRepository.get_by_name(db, session_name)
        
    def create_session(self, db: DBSession, session_name: str) -> Session:
        """
        Create a new session with the given name.
        
        Args:
            db: Database session
            session_name: Name for the new session
            
        Returns:
            Newly created Session object
        """
        session_create = SessionCreate(name=session_name)
        session = Session(name=session_create.name)
        return SessionRepository.create(db, session)

    def add_document(self, text: str) -> uuid.UUID:
        """
        Add a new document to the session.

        Args:
            text: The text content of the document.

        Returns:
            UUID of the created document.
        """
        # Implementation for adding a document

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

    def get_toponyms(self, recognition_module_name: str) -> list[dict]:
        """
        Get toponyms recognized by a specific recognition module.

        Args:
            recognition_module_name: Name of the recognition module.

        Returns:
            List of toponym dictionaries with relevant information.
        """
        # Implementation for retrieving toponyms

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
