import logging
import typing as t
from abc import ABC, abstractmethod
from uuid import UUID

from sqlmodel import Session as DBSession

from geoparser.db.crud import (
    DocumentRepository,
    LocationRepository,
    RecognitionModuleRepository,
    RecognitionRepository,
    ResolutionModuleRepository,
    ResolutionRepository,
    SessionRepository,
    ToponymRepository,
)
from geoparser.db.db import get_db
from geoparser.db.models import (
    Document,
    Location,
    LocationCreate,
    RecognitionCreate,
    RecognitionModule,
    RecognitionModuleCreate,
    ResolutionCreate,
    ResolutionModule,
    ResolutionModuleCreate,
    Session,
    Toponym,
    ToponymCreate,
)


class BaseModule(ABC):
    """
    Abstract base class for any GeoparserV2 module.

    All modules must implement this interface to be compatible
    with the GeoparserV2 architecture.

    The BaseModule handles database interactions, while child classes
    implement only the pure logic.
    """

    def __init__(self, name: str):
        """
        Initialize a module.

        Args:
            name: A unique name for this module
        """
        self.name = name
        self.module = None

    def run(self, session: Session) -> None:
        """
        Execute the module's functionality on the specified session.

        This method handles database session creation and cleanup,
        and delegates the actual execution to the _execute method.

        Args:
            session: Session object to process
        """
        # Get a database session
        db = next(get_db())

        try:
            # Call the abstract _execute method that child classes implement
            self._execute(db, session)

            # Commit changes to the database
            db.commit()

            logging.info(
                f"Module '{self.name}' completed successfully on session {session.name} ({session.id})"
            )
        except Exception as e:
            # Rollback in case of error
            db.rollback()
            logging.error(
                f"Error executing module '{self.name}' on session {session_id}: {str(e)}"
            )
            raise
        finally:
            # Close the database session
            db.close()

    @abstractmethod
    def _execute(self, db: DBSession, session: Session) -> None:
        """
        Execute the module's functionality with the provided database session.

        This abstract method must be implemented by child classes.

        Args:
            db: Database session
            session: Session object to process
        """


class RecognitionModule(BaseModule):
    """
    Abstract class for modules that perform toponym recognition.

    These modules identify potential toponyms in text and save them to the database.
    Recognition modules process documents and create toponym entries.

    The base class handles database interactions, while child classes
    implement only the toponym recognition logic.
    """

    def __init__(self, name: str):
        """
        Initialize a recognition module.

        Args:
            name: A unique name for this module
        """
        super().__init__(name)

        # Initialize module record in database
        self.module = self._initialize_module()

    def _initialize_module(self) -> RecognitionModule:
        """
        Initialize the module record in the database.

        Returns:
            The initialized RecognitionModule object
        """
        db = next(get_db())
        try:
            module = self._get_module(db)
            if module is None:
                module = self._create_module(db)
                db.commit()
            return module
        finally:
            db.close()

    def _get_module(self, db: DBSession) -> t.Optional[RecognitionModule]:
        """
        Get the module record from the database.

        Args:
            db: Database session

        Returns:
            RecognitionModule object if found, None otherwise
        """
        return RecognitionModuleRepository.get_by_name(db, self.name)

    def _create_module(self, db: DBSession) -> RecognitionModule:
        """
        Create a new module record in the database.

        Args:
            db: Database session

        Returns:
            Created RecognitionModule object
        """
        module_create = RecognitionModuleCreate(name=self.name)
        return RecognitionModuleRepository.create(db, module_create)

    def _get_documents(self, db: DBSession, session: Session) -> t.List[Document]:
        """
        Get all documents for a session.

        Args:
            db: Database session
            session: Session object

        Returns:
            List of documents
        """
        return DocumentRepository.get_by_session(db, session.id)

    def _document_has_been_processed(self, db: DBSession, document: Document) -> bool:
        """
        Check if a document has already been processed by this module.

        Args:
            db: Database session
            document: Document object

        Returns:
            True if the document has been processed, False otherwise
        """
        # Get all toponyms for the document
        toponyms = ToponymRepository.get_by_document(db, document.id)

        # If there are no toponyms, the document hasn't been processed
        if not toponyms:
            return False

        # Check if any of the toponyms have a recognition by this module
        for toponym in toponyms:
            recognitions = RecognitionRepository.get_by_toponym(db, toponym.id)
            if any(
                recognition.module_id == self.module.id for recognition in recognitions
            ):
                return True

        return False

    def _create_toponym(
        self, db: DBSession, document: Document, start: int, end: int
    ) -> Toponym:
        """
        Create a toponym and associate it with this recognition module.

        Args:
            db: Database session
            document: Document object
            start: Start position of the toponym in the document
            end: End position of the toponym in the document

        Returns:
            Created Toponym object
        """
        # Create the toponym
        toponym_create = ToponymCreate(start=start, end=end, document_id=document.id)
        toponym = ToponymRepository.create(db, toponym_create)

        # Create the recognition
        recognition_create = RecognitionCreate(
            toponym_id=toponym.id, module_id=self.module.id
        )
        RecognitionRepository.create(db, recognition_create)

        return toponym

    def _execute(self, db: DBSession, session: Session) -> None:
        """
        Execute toponym recognition on documents in the specified session.

        This method handles the database operations around the toponym recognition,
        calling the predict_toponyms method to get the actual toponyms.

        Args:
            db: Database session
            session: Session object to process
        """
        # Get all documents for the session
        documents = self._get_documents(db, session)

        for document in documents:
            # Skip documents that have already been processed by this module
            if self._document_has_been_processed(db, document):
                logging.info(
                    f"Document {document.id} already processed by module '{self.name}', skipping."
                )
                continue

            # Get toponyms predicted by child class
            predicted_toponyms = self.predict_toponyms(document.text)

            # Create toponyms and recognition records
            created_toponyms = []
            for start, end in predicted_toponyms:
                toponym = self._create_toponym(
                    db=db, document=document, start=start, end=end
                )
                created_toponyms.append(toponym)

            logging.info(
                f"Document {document.id} processed by module '{self.name}', {len(created_toponyms)} toponyms found."
            )

    @abstractmethod
    def predict_toponyms(self, text: str) -> t.List[t.Tuple[int, int]]:
        """
        Predict toponyms in a text.

        This abstract method must be implemented by child classes.

        Args:
            text: Text to process

        Returns:
            List of tuples containing (start, end) positions of toponyms
        """


class ResolutionModule(BaseModule):
    """
    Abstract class for modules that perform toponym resolution.

    These modules link recognized toponyms to specific locations in a gazetteer.
    Resolution modules process toponyms and create location entries.

    The base class handles database interactions, while child classes
    implement only the location resolution logic.
    """

    def __init__(self, name: str):
        """
        Initialize a resolution module.

        Args:
            name: A unique name for this module
        """
        super().__init__(name)

        # Initialize module record in database
        self.module = self._initialize_module()

    def _initialize_module(self) -> ResolutionModule:
        """
        Initialize the module record in the database.

        Returns:
            The initialized ResolutionModule object
        """
        db = next(get_db())
        try:
            module = self._get_module(db)
            if module is None:
                module = self._create_module(db)
                db.commit()
            return module
        finally:
            db.close()

    def _get_module(self, db: DBSession) -> t.Optional[ResolutionModule]:
        """
        Get the module record from the database.

        Args:
            db: Database session

        Returns:
            ResolutionModule object if found, None otherwise
        """
        return ResolutionModuleRepository.get_by_name(db, self.name)

    def _create_module(self, db: DBSession) -> ResolutionModule:
        """
        Create a new module record in the database.

        Args:
            db: Database session

        Returns:
            Created ResolutionModule object
        """
        module_create = ResolutionModuleCreate(name=self.name)
        return ResolutionModuleRepository.create(db, module_create)

    def _get_toponyms(
        self, db: DBSession, session: Session
    ) -> t.List[t.Tuple[Document, Toponym]]:
        """
        Get all toponyms for a session, together with their documents.

        Args:
            db: Database session
            session: Session object

        Returns:
            List of (document, toponym) tuples
        """
        # Get all documents for the session
        documents = DocumentRepository.get_by_session(db, session.id)

        doc_toponym_pairs = []
        for document in documents:
            # Get all toponyms for the document
            toponyms = ToponymRepository.get_by_document(db, document.id)
            for toponym in toponyms:
                doc_toponym_pairs.append((document, toponym))

        return doc_toponym_pairs

    def _toponym_has_been_processed(self, db: DBSession, toponym: Toponym) -> bool:
        """
        Check if a toponym has already been processed by this module.

        Args:
            db: Database session
            toponym: Toponym object

        Returns:
            True if the toponym has been processed, False otherwise
        """
        # Get all locations for the toponym
        locations = LocationRepository.get_by_toponym(db, toponym.id)

        # If there are no locations, the toponym hasn't been processed
        if not locations:
            return False

        # Check if any of the locations have a resolution by this module
        for location in locations:
            resolutions = ResolutionRepository.get_by_location(db, location.id)
            if any(
                resolution.module_id == self.module.id for resolution in resolutions
            ):
                return True

        return False

    def _create_location(
        self,
        db: DBSession,
        toponym: Toponym,
        location_id: str,
        confidence: t.Optional[float] = None,
    ) -> Location:
        """
        Create a location and associate it with this resolution module.

        Args:
            db: Database session
            toponym: Toponym object
            location_id: ID of the location in the gazetteer
            confidence: Optional confidence score

        Returns:
            Created Location object
        """
        # Create the location
        location_create = LocationCreate(
            location_id=location_id, confidence=confidence, toponym_id=toponym.id
        )
        location = LocationRepository.create(db, location_create)

        # Create the resolution
        resolution_create = ResolutionCreate(
            location_id=location.id, module_id=self.module.id
        )
        ResolutionRepository.create(db, resolution_create)

        return location

    def _execute(self, db: DBSession, session: Session) -> None:
        """
        Execute toponym resolution on toponyms in the specified session.

        This method handles the database operations around the location resolution,
        calling the predict_locations method to get the actual locations.

        Args:
            db: Database session
            session: Session object to process
        """
        # Get all toponyms for the session
        doc_toponym_pairs = self._get_toponyms(db, session)

        for document, toponym in doc_toponym_pairs:
            # Skip toponyms that have already been processed by this module
            if self._toponym_has_been_processed(db, toponym):
                logging.info(
                    f"Toponym {toponym.id} already processed by module '{self.name}', skipping."
                )
                continue

            # Extract toponym text from document
            toponym_text = document.text[toponym.start : toponym.end]

            # Get locations predicted by child class
            predicted_locations = self.predict_locations(
                document.text, toponym_text, toponym.start, toponym.end
            )

            # Create location and resolution records
            created_locations = []
            for location_id, confidence in predicted_locations:
                location = self._create_location(
                    db=db,
                    toponym=toponym,
                    location_id=location_id,
                    confidence=confidence,
                )
                created_locations.append(location)

            logging.info(
                f"Toponym {toponym.id} ('{toponym_text}') processed by module '{self.name}', {len(created_locations)} locations found."
            )

    @abstractmethod
    def predict_locations(
        self,
        document_text: str,
        toponym_text: str,
        toponym_start: int,
        toponym_end: int,
    ) -> t.List[t.Tuple[str, t.Optional[float]]]:
        """
        Predict locations for a toponym.

        This abstract method must be implemented by child classes.

        Args:
            document_text: Full text of the document
            toponym_text: Text of the toponym
            toponym_start: Start position of the toponym in the document
            toponym_end: End position of the toponym in the document

        Returns:
            List of tuples containing (location_id, confidence)
        """
