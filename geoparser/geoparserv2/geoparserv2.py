import logging
import typing as t
import uuid
from typing import List, Union

from sqlmodel import Session as DBSession

from geoparser.db.crud import DocumentRepository, SessionRepository
from geoparser.db.db import get_db
from geoparser.db.models import DocumentCreate, Session, SessionCreate
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
            session_name: Session name. Will load or create a session with this name.
        """
        self.session_id = self._initialize_session(session_name)
        self.session_name = session_name

    def _initialize_session(self, session_name: str) -> uuid.UUID:
        """
        Load an existing session or create a new one if it doesn't exist.

        Args:
            session_name: Name of the session to load or create

        Returns:
            Session ID that was loaded or created
        """
        db = next(get_db())
        session = self.load_session(db, session_name)

        if session is None:
            logging.info(
                f"No session found with name '{session_name}'; creating a new one."
            )
            session = self.create_session(db, session_name)

        return session.id

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

    def add_documents(self, texts: Union[str, List[str]]) -> List[uuid.UUID]:
        """
        Add one or more documents to the session.

        Args:
            texts: Either a single document text (str) or a list of document texts (List[str])

        Returns:
            List of UUIDs of the created documents
        """
        db = next(get_db())

        # Convert single string to list for uniform processing
        if isinstance(texts, str):
            texts = [texts]

        document_ids = []
        for text in texts:
            document_create = DocumentCreate(text=text, session_id=self.session_id)
            document = DocumentRepository.create(db, document_create)
            document_ids.append(document.id)

        return document_ids

    def run(self, module: BaseModule) -> None:
        """
        Run a processing module on the current session.

        This method will execute the specified module, which can be either
        a recognition module or a resolution module.

        Args:
            module: The module instance to run.
        """
        # Run the module on the session ID
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
