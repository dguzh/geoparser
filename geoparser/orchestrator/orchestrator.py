import uuid
from typing import List, Tuple

from sqlmodel import Session

from geoparser.db.crud import (
    DocumentRepository,
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
from geoparser.modules.recognizers.recognizer import Recognizer
from geoparser.modules.resolvers.resolver import Resolver


class Orchestrator:
    """
    Project-agnostic execution engine for a specific recognizer/resolver combination.

    This class is responsible for:
    - Initializing recognizer and resolver in the database
    - Running recognizer on documents to create references
    - Running resolver on references to create referents
    - Processing predictions and persisting them to the database

    The orchestrator works directly with documents and references, without
    knowledge of projects or project-specific filtering logic.
    """

    def __init__(self, recognizer: Recognizer, resolver: Resolver):
        """
        Initialize an Orchestrator for a specific recognizer/resolver combination.

        Args:
            recognizer: The recognizer to use
            resolver: The resolver to use
        """
        self.recognizer = recognizer
        self.resolver = resolver

        # Load recognizer and resolver IDs immediately
        self.recognizer_id = self._load_recognizer(recognizer)
        self.resolver_id = self._load_resolver(resolver)

    def _load_recognizer(self, module: Recognizer) -> uuid.UUID:
        """
        Load a recognizer from the database.

        Retrieves an existing recognizer record or creates a new one if it doesn't exist.

        Args:
            module: Recognizer to load

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

            return db_recognizer.id

    def _load_resolver(self, module: Resolver) -> uuid.UUID:
        """
        Load a resolver from the database.

        Retrieves an existing resolver record or creates a new one if it doesn't exist.

        Args:
            module: Resolver to load

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

            return db_resolver.id

    def run_recognizer(self, document_ids: List[uuid.UUID]) -> None:
        """
        Run the configured recognizer on the provided documents.

        Args:
            document_ids: List of document IDs to process
        """
        if not document_ids:
            return

        with Session(engine) as db:
            # Filter out documents that have already been processed by this recognizer
            unprocessed_document_ids = []
            for doc_id in document_ids:
                # Check if this document has already been processed by this recognizer
                existing_recognition = (
                    RecognitionRepository.get_by_document_and_recognizer(
                        db, doc_id, self.recognizer_id
                    )
                )
                if not existing_recognition:
                    unprocessed_document_ids.append(doc_id)

            if not unprocessed_document_ids:
                return

            # Get Document ORM objects for unprocessed documents
            unprocessed_documents = [
                DocumentRepository.get(db, doc_id)
                for doc_id in unprocessed_document_ids
            ]

            # Get predictions from recognizer using Document ORM objects
            predicted_references = self.recognizer.predict_references(
                unprocessed_documents
            )

            # Process predictions and update database
            self._process_reference_predictions(
                db, unprocessed_document_ids, predicted_references, self.recognizer_id
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
    ) -> None:
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
        ReferenceRepository.create(db, reference_create)

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

    def run_resolver(self, document_ids: List[uuid.UUID]) -> None:
        """
        Run the configured resolver on references from the provided documents.

        Args:
            document_ids: List of document IDs containing references to process
        """
        if not document_ids:
            return

        with Session(engine) as db:
            # Get all references from the specified documents
            all_references = []
            for doc_id in document_ids:
                references = ReferenceRepository.get_by_document(db, doc_id)
                all_references.extend(references)

            # Filter out references that have already been processed by this resolver
            unprocessed_references = []
            for ref in all_references:
                # Check if this reference has already been processed by this resolver
                existing_resolution = (
                    ResolutionRepository.get_by_reference_and_resolver(
                        db, ref.id, self.resolver_id
                    )
                )
                if not existing_resolution:
                    unprocessed_references.append(ref)

            if not unprocessed_references:
                return

            # Get predictions from resolver using Reference ORM objects directly
            predicted_referents = self.resolver.predict_referents(
                unprocessed_references
            )

            # Extract reference IDs for database operations
            reference_ids = [reference.id for reference in unprocessed_references]

            # Process predictions and update database
            self._process_referent_predictions(
                db, reference_ids, predicted_referents, self.resolver_id
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
    ) -> None:
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
        ReferentRepository.create(db, referent_create)

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
