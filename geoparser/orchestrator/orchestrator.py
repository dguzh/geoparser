import logging
import uuid
from typing import List, Tuple

from sqlmodel import Session

from geoparser.db.crud import (
    FeatureRepository,
    RecognitionRepository,
    RecognizerRepository,
    ReferenceRepository,
    ReferentRepository,
    ResolutionRepository,
    ResolverRepository,
)
from geoparser.db.db import engine
from geoparser.db.models import (
    RecognitionCreate,
    RecognizerCreate,
    ReferenceCreate,
    ReferentCreate,
    ResolutionCreate,
    ResolverCreate,
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
                # Initialize and execute recognizer
                recognizer_id = self._initialize_recognizer(module)
                self._execute_recognizer(module, recognizer_id, project_id)
            elif isinstance(module, Resolver):
                # Initialize and execute resolver
                resolver_id = self._initialize_resolver(module)
                self._execute_resolver(module, resolver_id, project_id)
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

    def _initialize_recognizer(self, module: Recognizer) -> uuid.UUID:
        """
        Initialize a recognizer in the database.

        Retrieves an existing recognizer record or creates a new one if it doesn't exist.

        Args:
            module: Recognizer to initialize

        Returns:
            Database ID of the recognizer
        """
        with Session(engine) as db:
            db_recognizer = RecognizerRepository.get_by_name_and_config(
                db, module.name, module.config
            )
            if db_recognizer is None:
                recognizer_create = RecognizerCreate(
                    name=module.name, config=module.config
                )
                db_recognizer = RecognizerRepository.create(db, recognizer_create)
                logging.info(f"Created new recognizer {str(module)}")
            else:
                logging.info(f"Using existing recognizer {str(module)}")

            return db_recognizer.id

    def _initialize_resolver(self, module: Resolver) -> uuid.UUID:
        """
        Initialize a resolver in the database.

        Retrieves an existing resolver record or creates a new one if it doesn't exist.

        Args:
            module: Resolver to initialize

        Returns:
            Database ID of the resolver
        """
        with Session(engine) as db:
            db_resolver = ResolverRepository.get_by_name_and_config(
                db, module.name, module.config
            )
            if db_resolver is None:
                resolver_create = ResolverCreate(name=module.name, config=module.config)
                db_resolver = ResolverRepository.create(db, resolver_create)
                logging.info(f"Created new resolver {str(module)}")
            else:
                logging.info(f"Using existing resolver {str(module)}")

            return db_resolver.id

    def _execute_recognizer(
        self,
        module: Recognizer,
        recognizer_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> None:
        """
        Execute a recognizer on unprocessed documents.

        Args:
            module: Recognizer to execute
            recognizer_id: Database ID of the recognizer
            project_id: UUID of the project to run the recognizer on
        """
        with Session(engine) as db:
            # Get unprocessed documents
            unprocessed_documents = self._get_unprocessed_documents(
                db, recognizer_id, project_id
            )

            if not unprocessed_documents:
                logging.info(
                    f"No unprocessed documents found for recognizer {str(module)}"
                )
                return

            logging.info(
                f"Processing {len(unprocessed_documents)} documents with recognizer {str(module)} in project {project_id}."
            )

            # Get predictions from module using Document ORM objects directly
            predicted_references = module.predict_references(unprocessed_documents)

            # Extract document IDs for database operations
            document_ids = [doc.id for doc in unprocessed_documents]

            # Process predictions and update database
            self._process_reference_predictions(
                db, document_ids, predicted_references, recognizer_id
            )

            logging.info(
                f"Recognizer {str(module)} completed processing {len(unprocessed_documents)} documents."
            )

    def _get_unprocessed_documents(
        self, db: Session, recognizer_id: uuid.UUID, project_id: uuid.UUID
    ):
        """
        Get documents that haven't been processed by a specific recognizer.

        Args:
            db: Database session
            recognizer_id: ID of the recognizer to check against
            project_id: UUID of the project to check against

        Returns:
            List of unprocessed documents
        """
        return RecognitionRepository.get_unprocessed_documents(
            db, project_id, recognizer_id
        )

    def _process_reference_predictions(
        self,
        db: Session,
        document_ids: List[uuid.UUID],
        predicted_references: List[List[Tuple[int, int]]],
        recognizer_id: uuid.UUID,
    ) -> None:
        """
        Process reference predictions and update the database.

        Args:
            db: Database session
            document_ids: List of document IDs
            predicted_references: Nested list of predicted references
            recognizer_id: ID of the recognizer that made the predictions
        """
        # Process each document with its predicted references
        for doc_id, references in zip(document_ids, predicted_references):
            # Create references with recognizer ID
            for start, end in references:
                self._create_reference_record(db, doc_id, start, end, recognizer_id)

            # Mark document as processed
            self._mark_document_processed(db, doc_id, recognizer_id)

    def _create_reference_record(
        self,
        db: Session,
        document_id: uuid.UUID,
        start: int,
        end: int,
        recognizer_id: uuid.UUID,
    ) -> uuid.UUID:
        """
        Create a reference record with the recognizer ID.

        Args:
            db: Database session
            document_id: ID of the document containing the reference
            start: Start position of the reference
            end: End position of the reference
            recognizer_id: ID of the recognizer

        Returns:
            ID of the created reference
        """
        # Create the reference with recognizer ID directly
        reference_create = ReferenceCreate(
            start=start, end=end, document_id=document_id, recognizer_id=recognizer_id
        )
        reference = ReferenceRepository.create(db, reference_create)

        return reference.id

    def _mark_document_processed(
        self, db: Session, document_id: uuid.UUID, recognizer_id: uuid.UUID
    ) -> None:
        """
        Mark a document as processed by a specific recognizer.

        Args:
            db: Database session
            document_id: ID of the document to mark
            recognizer_id: ID of the recognizer that processed it
        """
        recognition_create = RecognitionCreate(
            document_id=document_id, recognizer_id=recognizer_id
        )
        RecognitionRepository.create(db, recognition_create)

    def _execute_resolver(
        self,
        module: Resolver,
        resolver_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> None:
        """
        Execute a resolver on unprocessed references.

        Args:
            module: Resolver to execute
            resolver_id: Database ID of the resolver
            project_id: UUID of the project to run the resolver on
        """
        with Session(engine) as db:
            # Get unprocessed references
            unprocessed_references = self._get_unprocessed_references(
                db, resolver_id, project_id
            )

            if not unprocessed_references:
                logging.info(
                    f"No unprocessed references found for resolver {str(module)}"
                )
                return

            logging.info(
                f"Processing {len(unprocessed_references)} references with resolver {str(module)} in project {project_id}."
            )

            # Get predictions from module using Reference ORM objects directly
            predicted_referents = module.predict_referents(unprocessed_references)

            # Extract reference IDs for database operations
            reference_ids = [reference.id for reference in unprocessed_references]

            # Process predictions and update database
            self._process_referent_predictions(
                db, reference_ids, predicted_referents, resolver_id
            )

            logging.info(
                f"Resolver {str(module)} completed processing {len(unprocessed_references)} references."
            )

    def _get_unprocessed_references(
        self, db: Session, resolver_id: uuid.UUID, project_id: uuid.UUID
    ):
        """
        Get references that haven't been processed by a specific resolver.

        Args:
            db: Database session
            resolver_id: ID of the resolver to check against
            project_id: UUID of the project to check against

        Returns:
            List of unprocessed references
        """
        return ResolutionRepository.get_unprocessed_references(
            db, project_id, resolver_id
        )

    def _process_referent_predictions(
        self,
        db: Session,
        reference_ids: List[uuid.UUID],
        predicted_referents: List[List[Tuple[str, str]]],
        resolver_id: uuid.UUID,
    ) -> None:
        """
        Process referent predictions and update the database.

        Args:
            db: Database session
            reference_ids: List of reference IDs
            predicted_referents: Nested list of predicted (gazetteer_name, identifier) tuples
            resolver_id: ID of the resolver that made the predictions
        """
        # Process each reference with its predicted referents
        for reference_id, referents in zip(reference_ids, predicted_referents):
            # Create referent records for each prediction with resolver ID
            for gazetteer_name, identifier in referents:
                self._create_referent_record(
                    db, reference_id, gazetteer_name, identifier, resolver_id
                )

            # Mark reference as processed
            self._mark_reference_processed(db, reference_id, resolver_id)

    def _create_referent_record(
        self,
        db: Session,
        reference_id: uuid.UUID,
        gazetteer_name: str,
        identifier: str,
        resolver_id: uuid.UUID,
    ) -> uuid.UUID:
        """
        Create a referent record with the resolver ID.

        Args:
            db: Database session
            reference_id: ID of the reference
            gazetteer_name: Name of the gazetteer
            identifier: Identifier value in the gazetteer
            resolver_id: ID of the resolver

        Returns:
            ID of the created referent
        """
        # Look up the feature by gazetteer and identifier
        feature = FeatureRepository.get_by_gazetteer_and_identifier(
            db, gazetteer_name, identifier
        )

        # Create the referent with resolver ID directly
        referent_create = ReferentCreate(
            reference_id=reference_id, feature_id=feature.id, resolver_id=resolver_id
        )
        referent = ReferentRepository.create(db, referent_create)

        return referent.id

    def _mark_reference_processed(
        self, db: Session, reference_id: uuid.UUID, resolver_id: uuid.UUID
    ) -> None:
        """
        Mark a reference as processed by a specific resolver.

        Args:
            db: Database session
            reference_id: ID of the reference to mark
            resolver_id: ID of the resolver that processed it
        """
        resolution_create = ResolutionCreate(
            reference_id=reference_id, resolver_id=resolver_id
        )
        ResolutionRepository.create(db, resolution_create)
