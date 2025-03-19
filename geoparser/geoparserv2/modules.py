import logging
import typing as t
from abc import ABC, abstractmethod

from sqlmodel import Session as DBSession

from geoparser.db.crud import (
    LocationRepository,
    RecognitionModuleRepository,
    RecognitionObjectRepository,
    RecognitionSubjectRepository,
    ResolutionModuleRepository,
    ResolutionObjectRepository,
    ResolutionSubjectRepository,
    ToponymRepository,
)
from geoparser.db.db import get_db
from geoparser.db.models import (
    Document,
    Location,
    LocationCreate,
    RecognitionModule,
    RecognitionModuleCreate,
    RecognitionObjectCreate,
    RecognitionSubjectCreate,
    ResolutionModule,
    ResolutionModuleCreate,
    ResolutionObjectCreate,
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

    # Module name should be defined by subclasses
    NAME: str = None

    def __init__(self, config: t.Optional[dict] = None):
        """
        Initialize a module.

        Args:
            config: Optional configuration parameters for this module
        """
        if self.NAME is None:
            raise ValueError("Module must define a NAME class attribute")

        self.config = config or {}

        # Include the module name in the config to ensure uniqueness
        self.config["module_name"] = self.NAME

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
                f"Module '{self.NAME}' completed successfully on session {session.name} ({session.id})"
            )
        except Exception as e:
            # Rollback in case of error
            db.rollback()
            logging.error(
                f"Error executing module '{self.NAME}' on session {session.id}: {str(e)}"
            )
            raise
        finally:
            # Close the database session
            db.close()

    def get_config_string(self) -> str:
        """
        Get a string representation of the module's configuration.

        This can be used for logging and debugging purposes.

        Returns:
            String representation of the config
        """
        if not self.config or len(self.config) <= 1:  # Only module_name key
            return "no config"

        config_items = []
        for key, value in self.config.items():
            if key == "module_name":
                continue  # Skip the module name in the string representation

            if isinstance(value, str) and len(value) > 20:
                # Truncate long string values
                value_str = f"{value[:17]}..."
            else:
                value_str = str(value)
            config_items.append(f"{key}={value_str}")

        return ", ".join(config_items)

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

    # This base class should have NAME set to None since it should not be instantiated directly
    NAME = None

    def __init__(self, config: t.Optional[dict] = None):
        """
        Initialize a recognition module.

        Args:
            config: Optional configuration parameters for this module
        """
        super().__init__(config)

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
                logging.info(
                    f"Created new recognition module '{self.NAME}' with config: {self.get_config_string()}"
                )
            else:
                logging.info(
                    f"Using existing recognition module '{self.NAME}' with config: {self.get_config_string()}"
                )
            return module
        finally:
            db.close()

    def _get_module(self, db: DBSession) -> t.Optional[RecognitionModule]:
        """
        Get the module record from the database based on configuration.

        Args:
            db: Database session

        Returns:
            RecognitionModule object if found, None otherwise
        """
        return RecognitionModuleRepository.get_by_config(db, self.config)

    def _create_module(self, db: DBSession) -> RecognitionModule:
        """
        Create a new module record in the database.

        Args:
            db: Database session

        Returns:
            Created RecognitionModule object
        """
        module_create = RecognitionModuleCreate(config=self.config)
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

        logging.info(
            f"Processing {len(unprocessed_documents)} documents with module '{self.NAME}' (config: {self.get_config_string()}) in session {session.name}."
        )

        # Process each unprocessed document
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

            total_toponyms_created += len(created_toponyms)

            logging.info(
                f"Document {document.id} processed, {len(created_toponyms)} toponyms found."
            )

            # Create recognition subject for this document immediately
            subject_create = RecognitionSubjectCreate(
                document_id=document.id, module_id=self.module.id
            )
            RecognitionSubjectRepository.create(db, subject_create)

        logging.info(
            f"Module '{self.NAME}' (config: {self.get_config_string()}) completed processing {len(unprocessed_documents)} documents, "
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

    # This base class should have NAME set to None since it should not be instantiated directly
    NAME = None

    def __init__(self, config: t.Optional[dict] = None):
        """
        Initialize a resolution module.

        Args:
            config: Optional configuration parameters for this module
        """
        super().__init__(config)

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
                logging.info(
                    f"Created new resolution module '{self.NAME}' with config: {self.get_config_string()}"
                )
            else:
                logging.info(
                    f"Using existing resolution module '{self.NAME}' with config: {self.get_config_string()}"
                )
            return module
        finally:
            db.close()

    def _get_module(self, db: DBSession) -> t.Optional[ResolutionModule]:
        """
        Get the module record from the database based on configuration.

        Args:
            db: Database session

        Returns:
            ResolutionModule object if found, None otherwise
        """
        return ResolutionModuleRepository.get_by_config(db, self.config)

    def _create_module(self, db: DBSession) -> ResolutionModule:
        """
        Create a new module record in the database.

        Args:
            db: Database session

        Returns:
            Created ResolutionModule object
        """
        module_create = ResolutionModuleCreate(config=self.config)
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
        # Get all unprocessed toponyms for the session
        unprocessed_toponyms = ResolutionSubjectRepository.get_unprocessed_toponyms(
            db, session.id, self.module.id
        )

        logging.info(
            f"Processing {len(unprocessed_toponyms)} toponyms with module '{self.NAME}' (config: {self.get_config_string()}) in session {session.name}."
        )

        total_locations_created = 0

        for toponym in unprocessed_toponyms:
            # Get the document for this toponym
            document = toponym.document

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
                f"Toponym {toponym.id} ('{toponym_text}') processed, {len(created_locations)} locations found."
            )
            # Mark the current toponym as processed directly
            subject_create = ResolutionSubjectCreate(
                toponym_id=toponym.id, module_id=self.module.id
            )
            ResolutionSubjectRepository.create(db, subject_create)

            total_locations_created += len(created_locations)

        logging.info(
            f"Module '{self.NAME}' (config: {self.get_config_string()}) completed processing {len(unprocessed_toponyms)} toponyms, "
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
