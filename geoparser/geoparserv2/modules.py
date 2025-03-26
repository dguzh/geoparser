import logging
import typing as t
import uuid
from abc import ABC, abstractmethod

from sqlmodel import Session

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
    LocationCreate,
    RecognitionModule,
    RecognitionModuleCreate,
    RecognitionObjectCreate,
    RecognitionSubjectCreate,
    ResolutionModule,
    ResolutionModuleCreate,
    ResolutionObjectCreate,
    ResolutionSubjectCreate,
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

        # Initialize module record in database
        self.module_id = self._initialize_module()

    def _initialize_module(self):
        """
        Initialize the module record in the database.

        Returns:
            The initialized module ID
        """
        db = next(get_db())
        try:
            module = self._get_module(db)
            if module is None:
                module = self._create_module(db)
                db.commit()
                logging.info(
                    f"Created new {self.__class__.__name__.lower()} '{self.NAME}' with config: {self.get_config_string()}"
                )
            else:
                logging.info(
                    f"Using existing {self.__class__.__name__.lower()} '{self.NAME}' with config: {self.get_config_string()}"
                )
            return module.id
        finally:
            db.close()

    @abstractmethod
    def _get_module(self, db: Session):
        """
        Get the module record from the database based on configuration.

        Args:
            db: Database session

        Returns:
            Module object if found, None otherwise
        """

    @abstractmethod
    def _create_module(self, db: Session):
        """
        Create a new module record in the database.

        Args:
            db: Database session

        Returns:
            Created Module object
        """

    def run(self, project_id: uuid.UUID) -> None:
        """
        Execute the module's functionality on the specified project.

        This method handles database session creation and cleanup,
        and delegates the actual execution to the _execute method.

        Args:
            project_id: Project ID to process
        """
        # Get a database session
        db = next(get_db())

        try:
            # Call the abstract _execute method that child classes implement
            self._execute(db, project_id)

            # Commit changes to the database
            db.commit()

            logging.info(
                f"Module '{self.NAME}' completed successfully on project {project_id}"
            )
        except Exception as e:
            # Rollback in case of error
            db.rollback()
            logging.error(
                f"Error executing module '{self.NAME}' on project {project_id}: {str(e)}"
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
    def _execute(self, db: Session, project_id: uuid.UUID) -> None:
        """
        Execute the module's functionality with the provided database session.

        This abstract method must be implemented by child classes.

        Args:
            db: Database session
            project_id: Project ID to process
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

    def _get_module(self, db: Session) -> t.Optional[RecognitionModule]:
        """
        Get the module record from the database based on configuration.

        Args:
            db: Database session

        Returns:
            RecognitionModule object if found, None otherwise
        """
        return RecognitionModuleRepository.get_by_config(db, self.config)

    def _create_module(self, db: Session) -> RecognitionModule:
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
        self, db: Session, document_id: uuid.UUID, start: int, end: int
    ) -> uuid.UUID:
        """
        Create a toponym and associate it with this recognition module.

        Args:
            db: Database session
            document_id: ID of the document
            start: Start position of the toponym in the document
            end: End position of the toponym in the document

        Returns:
            Created Toponym ID
        """
        # Create the toponym
        toponym_create = ToponymCreate(start=start, end=end, document_id=document_id)
        toponym = ToponymRepository.create(db, toponym_create)

        # Create the recognition object
        recognition_object_create = RecognitionObjectCreate(
            toponym_id=toponym.id, module_id=self.module_id
        )
        RecognitionObjectRepository.create(db, recognition_object_create)

        return toponym.id

    def _create_recognition_subject(self, db: Session, document_id: uuid.UUID) -> None:
        """
        Create a recognition subject for a document.

        This marks the document as processed by this module.

        Args:
            db: Database session
            document_id: ID of the document to mark as processed
        """
        subject_create = RecognitionSubjectCreate(
            document_id=document_id, module_id=self.module_id
        )
        RecognitionSubjectRepository.create(db, subject_create)

    def _execute(self, db: Session, project_id: uuid.UUID) -> None:
        """
        Execute toponym recognition on documents in the specified project.

        This method handles the database operations around the toponym recognition,
        calling the predict_toponyms method to get the actual toponyms.

        Args:
            db: Database session
            project_id: Project ID to process
        """
        # Get all unprocessed documents for the project
        unprocessed_documents = RecognitionSubjectRepository.get_unprocessed_documents(
            db, project_id, self.module_id
        )

        logging.info(
            f"Processing {len(unprocessed_documents)} documents with module '{self.NAME}' (config: {self.get_config_string()}) in project {project_id}."
        )

        # Get document texts and IDs for prediction
        document_texts = [doc.text for doc in unprocessed_documents]
        document_ids = [doc.id for doc in unprocessed_documents]

        # Get toponyms predicted by child class in bulk
        predicted_toponyms = self.predict_toponyms(document_texts)

        # Process each document with its predicted toponyms
        for doc_id, toponyms in zip(document_ids, predicted_toponyms):
            # Create toponyms and recognition records
            for start, end in toponyms:
                toponym_id = self._create_toponym(
                    db=db, document_id=doc_id, start=start, end=end
                )

            # Create recognition subject for this document
            self._create_recognition_subject(db, doc_id)

        logging.info(
            f"Module '{self.NAME}' (config: {self.get_config_string()}) completed processing {len(unprocessed_documents)} documents."
        )

    @abstractmethod
    def predict_toponyms(
        self, document_texts: t.List[str]
    ) -> t.List[t.List[t.Tuple[int, int]]]:
        """
        Predict toponyms in multiple documents.

        This abstract method must be implemented by child classes.

        Args:
            document_texts: List of document texts to process

        Returns:
            List of lists of tuples containing (start, end) positions of toponyms.
            Each inner list corresponds to toponyms found in one document at the same index in the input list.
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

    def _get_module(self, db: Session) -> t.Optional[ResolutionModule]:
        """
        Get the module record from the database based on configuration.

        Args:
            db: Database session

        Returns:
            ResolutionModule object if found, None otherwise
        """
        return ResolutionModuleRepository.get_by_config(db, self.config)

    def _create_module(self, db: Session) -> ResolutionModule:
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
        db: Session,
        toponym_id: uuid.UUID,
        location_id: str,
        confidence: t.Optional[float] = None,
    ) -> uuid.UUID:
        """
        Create a location and associate it with this resolution module.

        Args:
            db: Database session
            toponym_id: ID of the toponym
            location_id: ID of the location in the gazetteer
            confidence: Optional confidence score

        Returns:
            Created Location ID
        """
        # Create the location
        location_create = LocationCreate(
            location_id=location_id, confidence=confidence, toponym_id=toponym_id
        )
        location = LocationRepository.create(db, location_create)

        # Create the resolution object
        resolution_object_create = ResolutionObjectCreate(
            location_id=location.id, module_id=self.module_id
        )
        ResolutionObjectRepository.create(db, resolution_object_create)

        return location.id

    def _create_resolution_subject(self, db: Session, toponym_id: uuid.UUID) -> None:
        """
        Create a resolution subject for a toponym.

        This marks the toponym as processed by this module.

        Args:
            db: Database session
            toponym_id: ID of the toponym to mark as processed
        """
        subject_create = ResolutionSubjectCreate(
            toponym_id=toponym_id, module_id=self.module_id
        )
        ResolutionSubjectRepository.create(db, subject_create)

    def _execute(self, db: Session, project_id: uuid.UUID) -> None:
        """
        Execute toponym resolution on toponyms in the specified project.

        This method handles the database operations around the location resolution,
        calling the predict_locations method to get the actual locations.

        Args:
            db: Database session
            project_id: Project ID to process
        """
        # Get all unprocessed toponyms for the project
        unprocessed_toponyms = ResolutionSubjectRepository.get_unprocessed_toponyms(
            db, project_id, self.module_id
        )

        logging.info(
            f"Processing {len(unprocessed_toponyms)} toponyms with module '{self.NAME}' (config: {self.get_config_string()}) in project {project_id}."
        )

        # Prepare input data for prediction
        toponym_data = [
            {
                "start": toponym.start,
                "end": toponym.end,
                "document_text": toponym.document.text,
            }
            for toponym in unprocessed_toponyms
        ]

        toponym_ids = [toponym.id for toponym in unprocessed_toponyms]

        # Get locations predicted by child class in bulk
        predicted_locations = self.predict_locations(toponym_data)

        # Process each toponym with its predicted locations
        for toponym_id, locations in zip(toponym_ids, predicted_locations):
            # Create location and resolution records
            for location_id, confidence in locations:
                location_id = self._create_location(
                    db=db,
                    toponym_id=toponym_id,
                    location_id=location_id,
                    confidence=confidence,
                )

            # Mark the current toponym as processed
            self._create_resolution_subject(db, toponym_id=toponym_id)

        logging.info(
            f"Module '{self.NAME}' (config: {self.get_config_string()}) completed processing {len(unprocessed_toponyms)} toponyms."
        )

    @abstractmethod
    def predict_locations(
        self, toponym_data: t.List[dict]
    ) -> t.List[t.List[t.Tuple[str, t.Optional[float]]]]:
        """
        Predict locations for multiple toponyms.

        This abstract method must be implemented by child classes.

        Args:
            toponym_data: List of dictionaries containing toponym information:
                          - start: start position in document
                          - end: end position in document
                          - document_text: full document text

        Returns:
            List of lists of tuples containing (location_id, confidence).
            Each inner list corresponds to locations found for one toponym at the same index in the input list.
        """
