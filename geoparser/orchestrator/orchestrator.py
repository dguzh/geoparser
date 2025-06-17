import logging
import uuid
from typing import List, Tuple

from sqlmodel import Session

from geoparser.db.crud import (
    FeatureRepository,
    RecognitionModuleRepository,
    RecognitionObjectRepository,
    RecognitionSubjectRepository,
    ReferenceRepository,
    ReferentRepository,
    ResolutionModuleRepository,
    ResolutionObjectRepository,
    ResolutionSubjectRepository,
)
from geoparser.db.db import engine
from geoparser.db.models import (
    RecognitionModuleCreate,
    RecognitionObjectCreate,
    RecognitionSubjectCreate,
    ReferenceCreate,
    ReferentCreate,
    ResolutionModuleCreate,
    ResolutionObjectCreate,
    ResolutionSubjectCreate,
)
from geoparser.modules.module import Module
from geoparser.modules.recognizers.recognizer import Recognizer
from geoparser.modules.resolvers.resolver import Resolver


class Orchestrator:
    """
    Manages the execution and database interactions for geoparser modules.

    This class is responsible for all module-related operations including:
    - Initializing modules in the database (retrieving or creating module records)
    - Executing modules on the appropriate data
    - Processing module predictions and persisting them to the database
    - Tracking module execution state for processed documents and references
    """

    def __init__(self):
        """
        Initialize an Orchestrator.
        """

    def run_module(self, module: Module, project_id: uuid.UUID) -> None:
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
            if isinstance(module, Recognizer):
                # Initialize and execute recognition module
                module_id = self._initialize_recognition_module(module)
                self._execute_recognition_module(module, module_id, project_id)
            elif isinstance(module, Resolver):
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

    def _initialize_recognition_module(self, module: Recognizer) -> uuid.UUID:
        """
        Initialize a recognition module in the database.

        Retrieves an existing module record or creates a new one if it doesn't exist.

        Args:
            module: Recognition module to initialize

        Returns:
            Database ID of the module
        """
        with Session(engine) as db:
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

    def _initialize_resolution_module(self, module: Resolver) -> uuid.UUID:
        """
        Initialize a resolution module in the database.

        Retrieves an existing module record or creates a new one if it doesn't exist.

        Args:
            module: Resolution module to initialize

        Returns:
            Database ID of the module
        """
        with Session(engine) as db:
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
        self,
        module: Recognizer,
        module_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> None:
        """
        Execute a recognition module on unprocessed documents.

        Args:
            module: Recognition module to execute
            module_id: Database ID of the module
            project_id: UUID of the project to run the module on
        """
        with Session(engine) as db:
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
            predicted_references = module.predict_references(document_texts)

            # Process predictions and update database
            self._process_reference_predictions(
                db, document_ids, predicted_references, module_id
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

    def _process_reference_predictions(
        self,
        db: Session,
        document_ids: List[uuid.UUID],
        predicted_references: List[List[Tuple[int, int]]],
        module_id: uuid.UUID,
    ) -> None:
        """
        Process reference predictions and update the database.

        Args:
            db: Database session
            document_ids: List of document IDs
            predicted_references: Nested list of predicted references
            module_id: ID of the module that made the predictions
        """
        # Process each document with its predicted references
        for doc_id, references in zip(document_ids, predicted_references):
            # Create references and recognition records
            for start, end in references:
                self._create_reference_record(db, doc_id, start, end, module_id)

            # Mark document as processed
            self._mark_document_processed(db, doc_id, module_id)

    def _create_reference_record(
        self,
        db: Session,
        document_id: uuid.UUID,
        start: int,
        end: int,
        module_id: uuid.UUID,
    ) -> uuid.UUID:
        """
        Create a reference record and associate it with a recognition module.

        Args:
            db: Database session
            document_id: ID of the document containing the reference
            start: Start position of the reference
            end: End position of the reference
            module_id: ID of the recognition module

        Returns:
            ID of the created reference
        """
        # Check if a reference with the same span already exists for this document
        reference = ReferenceRepository.get_by_document_and_span(
            db, document_id, start, end
        )

        # If not, create the reference
        if reference is None:
            # Create the reference
            reference_create = ReferenceCreate(
                start=start, end=end, document_id=document_id
            )
            reference = ReferenceRepository.create(db, reference_create)

        # Create the recognition object (link between reference and module)
        recognition_object_create = RecognitionObjectCreate(
            reference_id=reference.id, module_id=module_id
        )
        RecognitionObjectRepository.create(db, recognition_object_create)

        return reference.id

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
        self,
        module: Resolver,
        module_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> None:
        """
        Execute a resolution module on unprocessed references.

        Args:
            module: Resolution module to execute
            module_id: Database ID of the module
            project_id: UUID of the project to run the module on
        """
        with Session(engine) as db:
            # Get unprocessed references
            unprocessed_references = self._get_unprocessed_references(
                db, module_id, project_id
            )

            if not unprocessed_references:
                logging.info(
                    f"No unprocessed references found for module {str(module)}"
                )
                return

            logging.info(
                f"Processing {len(unprocessed_references)} references with module {str(module)} in project {project_id}."
            )

            # Prepare input data for module
            reference_data = [
                {
                    "start": reference.start,
                    "end": reference.end,
                    "text": reference.text,
                    "document_text": reference.document.text,
                }
                for reference in unprocessed_references
            ]
            reference_ids = [reference.id for reference in unprocessed_references]

            # Get predictions from module
            predicted_referents = module.predict_referents(reference_data)

            # Process predictions and update database
            self._process_referent_predictions(
                db, reference_ids, predicted_referents, module_id
            )

            logging.info(
                f"Module {str(module)} completed processing {len(unprocessed_references)} references."
            )

    def _get_unprocessed_references(
        self, db: Session, module_id: uuid.UUID, project_id: uuid.UUID
    ):
        """
        Get references that haven't been processed by a specific resolution module.

        Args:
            db: Database session
            module_id: ID of the module to check against
            project_id: UUID of the project to check against

        Returns:
            List of unprocessed references
        """
        return ResolutionSubjectRepository.get_unprocessed_references(
            db, project_id, module_id
        )

    def _process_referent_predictions(
        self,
        db: Session,
        reference_ids: List[uuid.UUID],
        predicted_referents: List[List[Tuple[str, str]]],
        module_id: uuid.UUID,
    ) -> None:
        """
        Process referent predictions and update the database.

        Args:
            db: Database session
            reference_ids: List of reference IDs
            predicted_referents: Nested list of predicted (gazetteer_name, identifier) tuples
            module_id: ID of the module that made the predictions
        """
        # Process each reference with its predicted referents
        for reference_id, referents in zip(reference_ids, predicted_referents):
            # Create referent records for each prediction
            for gazetteer_name, identifier in referents:
                self._create_referent_record(
                    db, reference_id, gazetteer_name, identifier, module_id
                )

            # Mark reference as processed
            self._mark_reference_processed(db, reference_id, module_id)

    def _create_referent_record(
        self,
        db: Session,
        reference_id: uuid.UUID,
        gazetteer_name: str,
        identifier: str,
        module_id: uuid.UUID,
    ) -> uuid.UUID:
        """
        Create a referent record and associate it with a resolution module.

        Args:
            db: Database session
            reference_id: ID of the reference
            gazetteer_name: Name of the gazetteer
            identifier: Identifier value in the gazetteer
            module_id: ID of the resolution module

        Returns:
            ID of the created referent
        """
        # Look up the feature by gazetteer and identifier
        feature = FeatureRepository.get_by_gazetteer_and_identifier(
            db, gazetteer_name, identifier
        )

        # Create the referent
        referent_create = ReferentCreate(
            reference_id=reference_id, feature_id=feature.id
        )
        referent = ReferentRepository.create(db, referent_create)

        # Create the resolution object (link between referent and module)
        resolution_object_create = ResolutionObjectCreate(
            referent_id=referent.id, module_id=module_id
        )
        ResolutionObjectRepository.create(db, resolution_object_create)

        return referent.id

    def _mark_reference_processed(
        self, db: Session, reference_id: uuid.UUID, module_id: uuid.UUID
    ) -> None:
        """
        Mark a reference as processed by a specific module.

        Args:
            db: Database session
            reference_id: ID of the reference to mark
            module_id: ID of the module that processed it
        """
        subject_create = ResolutionSubjectCreate(
            reference_id=reference_id, module_id=module_id
        )
        ResolutionSubjectRepository.create(db, subject_create)
