import logging
import typing as t
from abc import ABC, abstractmethod
from uuid import UUID

from sqlmodel import Session as DBSession

from geoparser.db.crud import (
    DocumentRepository,
    LocationRepository,
    RecognitionModuleRepository,
    RecognitionSubjectRepository,
    RecognitionObjectRepository,
    ResolutionModuleRepository,
    ResolutionSubjectRepository,
    ResolutionObjectRepository,
    SessionRepository,
    ToponymRepository,
)
from geoparser.db.db import get_db
from geoparser.db.models import (
    Document,
    Location,
    LocationCreate,
    RecognitionObjectCreate,
    RecognitionModule,
    RecognitionModuleCreate,
    RecognitionSubject,
    RecognitionSubjectCreate,
    ResolutionObjectCreate,
    ResolutionModule,
    ResolutionModuleCreate,
    ResolutionSubject,
    ResolutionSubjectCreate,
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
                f"Error executing module '{self.name}' on session {session.id}: {str(e)}"
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

        # Create the recognition object
        recognition_object_create = RecognitionObjectCreate(
            toponym_id=toponym.id, module_id=self.module.id
        )
        RecognitionObjectRepository.create(db, recognition_object_create)

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
        # Get all unprocessed documents for the session
        unprocessed_documents = RecognitionSubjectRepository.get_unprocessed_documents(
            db, session.id, self.module.id
        )
        
        if not unprocessed_documents:
            logging.info(
                f"No unprocessed documents found for module '{self.name}' in session {session.name}."
            )
            return
            
        logging.info(
            f"Processing {len(unprocessed_documents)} unprocessed documents with module '{self.name}'."
        )
        
        # Process each unprocessed document
        processed_document_ids = []
        total_toponyms_created = 0
        
        for document in unprocessed_documents:
            # Get toponyms predicted by child class
            predicted_toponyms = self.predict_toponyms(document.text)

            # Create toponyms and recognition records
            created_toponyms = []
            for start, end in predicted_toponyms:
                toponym = self._create_toponym(
                    db=db, document=document, start=start, end=end
                )
                created_toponyms.append(toponym)
            
            # Add document to the list of processed documents
            processed_document_ids.append(document.id)
            total_toponyms_created += len(created_toponyms)
            
            logging.info(
                f"Document {document.id} processed, {len(created_toponyms)} toponyms found."
            )
        
        # Mark all documents as processed in a batch operation
        if processed_document_ids:
            RecognitionSubjectRepository.create_many(
                db, processed_document_ids, self.module.id
            )
            
        logging.info(
            f"Module '{self.name}' completed processing {len(processed_document_ids)} documents, "
            f"creating {total_toponyms_created} toponyms in total."
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

        # Create the resolution object
        resolution_object_create = ResolutionObjectCreate(
            location_id=location.id, module_id=self.module.id
        )
        ResolutionObjectRepository.create(db, resolution_object_create)

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
        # Get all unprocessed toponyms with their documents for the session
        unprocessed_items = ResolutionSubjectRepository.get_unprocessed_toponyms_with_documents(
            db, session.id, self.module.id
        )
        
        if not unprocessed_items:
            logging.info(
                f"No unprocessed toponyms found for module '{self.name}' in session {session.name}."
            )
            return
            
        logging.info(
            f"Processing {len(unprocessed_items)} unprocessed toponyms with module '{self.name}'."
        )
        
        # Process each unprocessed toponym
        processed_toponym_ids = []
        total_locations_created = 0
        
        for document, toponym in unprocessed_items:
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
            
            # Add toponym to the list of processed toponyms
            processed_toponym_ids.append(toponym.id)
            total_locations_created += len(created_locations)
            
            logging.info(
                f"Toponym {toponym.id} ('{toponym_text}') processed, {len(created_locations)} locations found."
            )
        
        # Mark all toponyms as processed in a batch operation
        if processed_toponym_ids:
            ResolutionSubjectRepository.create_many(
                db, processed_toponym_ids, self.module.id
            )
            
        logging.info(
            f"Module '{self.name}' completed processing {len(processed_toponym_ids)} toponyms, "
            f"creating {total_locations_created} locations in total."
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
