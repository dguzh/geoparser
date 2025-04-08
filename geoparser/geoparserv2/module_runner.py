import logging
import uuid
from typing import List, Optional, Tuple

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
    RecognitionModuleCreate,
    RecognitionObjectCreate,
    RecognitionSubjectCreate,
    ResolutionModuleCreate,
    ResolutionObjectCreate,
    ResolutionSubjectCreate,
    ToponymCreate,
)
from geoparser.geoparserv2.module_interfaces import (
    BaseModule,
    RecognitionModule,
    ResolutionModule,
)


class ModuleRunner:
    """
    Manages the execution and database interactions for geoparser modules.

    This class is responsible for all module-related operations including:
    - Initializing modules in the database (retrieving or creating module records)
    - Executing modules on the appropriate data
    - Processing module predictions and persisting them to the database
    - Tracking module execution state for processed documents and toponyms
    """

    def __init__(self):
        """
        Initialize a ModuleRunner.
        """

    def run_module(self, module: BaseModule, project_id: uuid.UUID) -> None:
        """
        Run a module on a specific project.

        This method handles the execution of the module, including database
        interactions and error handling.

        Args:
            module: The module to run
            project_id: UUID of the project to run the module on
        """
        try:
            # Execute based on module type
            if isinstance(module, RecognitionModule):
                # Initialize and execute recognition module
                module_id = self._initialize_recognition_module(module)
                self._execute_recognition_module(module, module_id, project_id)
            elif isinstance(module, ResolutionModule):
                # Initialize and execute resolution module
                module_id = self._initialize_resolution_module(module)
                self._execute_resolution_module(module, module_id, project_id)
            else:
                raise ValueError(f"Unsupported module type: {type(module)}")

            logging.info(
                f"Module {str(module)} completed successfully on project {project_id}"
            )
        except Exception as e:
            logging.error(
                f"Error executing module {str(module)} on project {project_id}: {str(e)}"
            )
            raise

    def _initialize_recognition_module(self, module: RecognitionModule) -> uuid.UUID:
        """
        Initialize a recognition module in the database.

        Retrieves an existing module record or creates a new one if it doesn't exist.

        Args:
            module: Recognition module to initialize

        Returns:
            Database ID of the module
        """
        db = next(get_db())

        db_module = RecognitionModuleRepository.get_by_name_and_config(
            db, module.name, module.config
        )
        if db_module is None:
            module_create = RecognitionModuleCreate(
                name=module.name, config=module.config
            )
            db_module = RecognitionModuleRepository.create(db, module_create)
            logging.info(f"Created new recognition module {str(module)}")
        else:
            logging.info(f"Using existing recognition module {str(module)}")

        return db_module.id

    def _initialize_resolution_module(self, module: ResolutionModule) -> uuid.UUID:
        """
        Initialize a resolution module in the database.

        Retrieves an existing module record or creates a new one if it doesn't exist.

        Args:
            module: Resolution module to initialize

        Returns:
            Database ID of the module
        """
        db = next(get_db())

        db_module = ResolutionModuleRepository.get_by_name_and_config(
            db, module.name, module.config
        )
        if db_module is None:
            module_create = ResolutionModuleCreate(
                name=module.name, config=module.config
            )
            db_module = ResolutionModuleRepository.create(db, module_create)
            logging.info(f"Created new resolution module {str(module)}")
        else:
            logging.info(f"Using existing resolution module {str(module)}")

        return db_module.id

    def _execute_recognition_module(
        self, module: RecognitionModule, module_id: uuid.UUID, project_id: uuid.UUID
    ) -> None:
        """
        Execute a recognition module on unprocessed documents.

        Args:
            module: Recognition module to execute
            module_id: Database ID of the module
            project_id: UUID of the project to run the module on
        """
        db = next(get_db())

        # Get unprocessed documents
        unprocessed_documents = self._get_unprocessed_documents(
            db, module_id, project_id
        )

        if not unprocessed_documents:
            logging.info(f"No unprocessed documents found for module {str(module)}")
            return

        logging.info(
            f"Processing {len(unprocessed_documents)} documents with module {str(module)} in project {project_id}."
        )

        # Prepare input data for module
        document_texts = [doc.text for doc in unprocessed_documents]
        document_ids = [doc.id for doc in unprocessed_documents]

        # Get predictions from module
        predicted_toponyms = module.predict_toponyms(document_texts)

        # Process predictions and update database
        self._process_toponym_predictions(
            db, document_ids, predicted_toponyms, module_id
        )

        logging.info(
            f"Module {str(module)} completed processing {len(unprocessed_documents)} documents."
        )

    def _get_unprocessed_documents(
        self, db: Session, module_id: uuid.UUID, project_id: uuid.UUID
    ):
        """
        Get documents that haven't been processed by a specific module.

        Args:
            db: Database session
            module_id: ID of the module to check against
            project_id: UUID of the project to check against

        Returns:
            List of unprocessed documents
        """
        return RecognitionSubjectRepository.get_unprocessed_documents(
            db, project_id, module_id
        )

    def _process_toponym_predictions(
        self,
        db: Session,
        document_ids: List[uuid.UUID],
        predicted_toponyms: List[List[Tuple[int, int]]],
        module_id: uuid.UUID,
    ) -> None:
        """
        Process toponym predictions and update the database.

        Args:
            db: Database session
            document_ids: List of document IDs
            predicted_toponyms: Nested list of predicted toponyms
            module_id: ID of the module that made the predictions
        """
        # Process each document with its predicted toponyms
        for doc_id, toponyms in zip(document_ids, predicted_toponyms):
            # Create toponyms and recognition records
            for start, end in toponyms:
                self._create_toponym_record(db, doc_id, start, end, module_id)

            # Mark document as processed
            self._mark_document_processed(db, doc_id, module_id)

    def _create_toponym_record(
        self,
        db: Session,
        document_id: uuid.UUID,
        start: int,
        end: int,
        module_id: uuid.UUID,
    ) -> uuid.UUID:
        """
        Create a toponym record and associate it with a recognition module.

        Args:
            db: Database session
            document_id: ID of the document containing the toponym
            start: Start position of the toponym
            end: End position of the toponym
            module_id: ID of the recognition module

        Returns:
            ID of the created toponym
        """
        # Check if a toponym with the same span already exists for this document
        toponym = ToponymRepository.get_by_document_and_span(
            db, document_id, start, end
        )

        # If not, create the toponym
        if toponym is None:
            # Create the toponym
            toponym_create = ToponymCreate(
                start=start, end=end, document_id=document_id
            )
            toponym = ToponymRepository.create(db, toponym_create)

        # Create the recognition object (link between toponym and module)
        recognition_object_create = RecognitionObjectCreate(
            toponym_id=toponym.id, module_id=module_id
        )
        RecognitionObjectRepository.create(db, recognition_object_create)

        return toponym.id

    def _mark_document_processed(
        self, db: Session, document_id: uuid.UUID, module_id: uuid.UUID
    ) -> None:
        """
        Mark a document as processed by a specific module.

        Args:
            db: Database session
            document_id: ID of the document to mark
            module_id: ID of the module that processed it
        """
        subject_create = RecognitionSubjectCreate(
            document_id=document_id, module_id=module_id
        )
        RecognitionSubjectRepository.create(db, subject_create)

    def _execute_resolution_module(
        self, module: ResolutionModule, module_id: uuid.UUID, project_id: uuid.UUID
    ) -> None:
        """
        Execute a resolution module on unprocessed toponyms.

        Args:
            module: Resolution module to execute
            module_id: Database ID of the module
            project_id: UUID of the project to run the module on
        """
        db = next(get_db())

        # Get unprocessed toponyms
        unprocessed_toponyms = self._get_unprocessed_toponyms(db, module_id, project_id)

        if not unprocessed_toponyms:
            logging.info(f"No unprocessed toponyms found for module {str(module)}")
            return

        logging.info(
            f"Processing {len(unprocessed_toponyms)} toponyms with module {str(module)} in project {project_id}."
        )

        # Prepare input data for module
        toponym_data = [
            {
                "start": toponym.start,
                "end": toponym.end,
                "text": toponym.text,
                "document_text": toponym.document.text,
            }
            for toponym in unprocessed_toponyms
        ]
        toponym_ids = [toponym.id for toponym in unprocessed_toponyms]

        # Get predictions from module
        predicted_locations = module.predict_locations(toponym_data)

        # Process predictions and update database
        self._process_location_predictions(
            db, toponym_ids, predicted_locations, module_id
        )

        logging.info(
            f"Module {str(module)} completed processing {len(unprocessed_toponyms)} toponyms."
        )

    def _get_unprocessed_toponyms(
        self, db: Session, module_id: uuid.UUID, project_id: uuid.UUID
    ):
        """
        Get toponyms that haven't been processed by a specific resolution module.

        Args:
            db: Database session
            module_id: ID of the module to check against
            project_id: UUID of the project to check against

        Returns:
            List of unprocessed toponyms
        """
        return ResolutionSubjectRepository.get_unprocessed_toponyms(
            db, project_id, module_id
        )

    def _process_location_predictions(
        self,
        db: Session,
        toponym_ids: List[uuid.UUID],
        predicted_locations: List[List[Tuple[str, Optional[float]]]],
        module_id: uuid.UUID,
    ) -> None:
        """
        Process location predictions and update the database.

        Args:
            db: Database session
            toponym_ids: List of toponym IDs
            predicted_locations: Nested list of predicted locations
            module_id: ID of the module that made the predictions
        """
        # Process each toponym with its predicted locations
        for toponym_id, locations in zip(toponym_ids, predicted_locations):
            # Create location records for each prediction
            for location_id, confidence in locations:
                self._create_location_record(
                    db, toponym_id, location_id, confidence, module_id
                )

            # Mark toponym as processed
            self._mark_toponym_processed(db, toponym_id, module_id)

    def _create_location_record(
        self,
        db: Session,
        toponym_id: uuid.UUID,
        location_id: str,
        confidence: Optional[float],
        module_id: uuid.UUID,
    ) -> uuid.UUID:
        """
        Create a location record and associate it with a resolution module.

        Args:
            db: Database session
            toponym_id: ID of the toponym
            location_id: ID of the location in the gazetteer
            confidence: Optional confidence score
            module_id: ID of the resolution module

        Returns:
            ID of the created location
        """
        # Create the location
        location_create = LocationCreate(
            location_id=location_id, confidence=confidence, toponym_id=toponym_id
        )
        location = LocationRepository.create(db, location_create)

        # Create the resolution object (link between location and module)
        resolution_object_create = ResolutionObjectCreate(
            location_id=location.id, module_id=module_id
        )
        ResolutionObjectRepository.create(db, resolution_object_create)

        return location.id

    def _mark_toponym_processed(
        self, db: Session, toponym_id: uuid.UUID, module_id: uuid.UUID
    ) -> None:
        """
        Mark a toponym as processed by a specific module.

        Args:
            db: Database session
            toponym_id: ID of the toponym to mark
            module_id: ID of the module that processed it
        """
        subject_create = ResolutionSubjectCreate(
            toponym_id=toponym_id, module_id=module_id
        )
        ResolutionSubjectRepository.create(db, subject_create)
