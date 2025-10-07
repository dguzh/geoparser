import typing as t
import uuid
from abc import abstractmethod
from typing import List, Tuple

from sqlmodel import Session

from geoparser.db.crud import (
    FeatureRepository,
    ReferenceRepository,
    ReferentRepository,
    ResolutionRepository,
    ResolverRepository,
)
from geoparser.db.engine import engine
from geoparser.db.models import ReferentCreate, ResolutionCreate, ResolverCreate
from geoparser.modules.module import Module

if t.TYPE_CHECKING:
    from geoparser.db.models import Document, Reference


class Resolver(Module):
    """
    Abstract class for modules that perform reference resolution.

    These modules link recognized references to specific referents in a gazetteer
    and handle all database operations related to resolution processing.
    """

    # This base class should have NAME set to None since it should not be instantiated directly
    NAME = None

    def __init__(self, **kwargs):
        """
        Initialize a resolution module.

        Args:
            **kwargs: Configuration parameters for this module
        """
        super().__init__(**kwargs)

        # Load resolver ID immediately upon initialization
        self.id = self._load()

    def _load(self) -> uuid.UUID:
        """
        Load a resolver from the database.

        Retrieves an existing resolver record or creates a new one if it doesn't exist.

        Returns:
            Database ID of the resolver
        """
        with Session(engine) as db:
            db_resolver = ResolverRepository.get_by_name_and_config(
                db, self.name, self.config
            )
            if db_resolver is None:
                resolver_create = ResolverCreate(name=self.name, config=self.config)
                db_resolver = ResolverRepository.create(db, resolver_create)

            return db_resolver.id

    def run(self, documents: List["Document"]) -> None:
        """
        Run the configured resolver on all references from the provided documents.

        Args:
            documents: List of Document objects containing references to process
        """
        if not documents:
            return

        with Session(engine) as db:
            # Collect data for prediction
            texts = []
            reference_boundaries = []
            reference_objects = []

            for doc in documents:
                # Get all references for this document
                references = ReferenceRepository.get_by_document(db, doc.id)

                # Filter to unprocessed references only
                unprocessed_references = self._filter_unprocessed_references(
                    db, references
                )

                # Only add to lists if there are unprocessed references
                if unprocessed_references:
                    texts.append(doc.text)
                    reference_boundaries.append(
                        [(ref.start, ref.end) for ref in unprocessed_references]
                    )
                    reference_objects.append(unprocessed_references)

            # Only call predict_referents if there are documents with unprocessed references
            if texts:
                # Get predictions from resolver using raw data
                predicted_referents = self.predict_referents(
                    texts, reference_boundaries
                )

                # Record predictions for each document
                for unprocessed_references, doc_referents in zip(
                    reference_objects, predicted_referents
                ):
                    self._record_referent_predictions(
                        db, unprocessed_references, doc_referents, self.id
                    )

    def _record_referent_predictions(
        self,
        db: Session,
        unprocessed_references: List["Reference"],
        predicted_referents: List[Tuple[str, str]],
        resolver_id: uuid.UUID,
    ) -> None:
        """
        Process referent predictions and update the database.

        Args:
            db: Database session
            unprocessed_references: List of references to process
            predicted_referents: List of (gazetteer_name, identifier) tuples - each reference gets exactly one referent
            resolver_id: ID of the resolver that made the predictions
        """
        # Process each reference with its predicted referent
        for reference, referent in zip(unprocessed_references, predicted_referents):
            # Create referent record for the single prediction with resolver ID
            gazetteer_name, identifier = referent
            self._create_referent_record(
                db, reference.id, gazetteer_name, identifier, resolver_id
            )

            # Mark reference as processed
            self._create_resolution_record(db, reference.id, resolver_id)

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

    def _create_resolution_record(
        self, db: Session, reference_id: uuid.UUID, resolver_id: uuid.UUID
    ) -> None:
        """
        Create a resolution record for a reference processed by a specific resolver.

        Args:
            db: Database session
            reference_id: ID of the reference that was processed
            resolver_id: ID of the resolver that processed it
        """
        resolution_create = ResolutionCreate(
            reference_id=reference_id, resolver_id=resolver_id
        )
        ResolutionRepository.create(db, resolution_create)

    def _filter_unprocessed_references(
        self, db: Session, references: List["Reference"]
    ) -> List["Reference"]:
        """
        Filter out references that have already been processed by this resolver.

        Args:
            db: Database session
            references: List of references to check

        Returns:
            List of references that haven't been processed by this resolver.
        """
        unprocessed_references = []
        for ref in references:
            # Check if this reference has already been processed by this resolver
            existing_resolution = ResolutionRepository.get_by_reference_and_resolver(
                db, ref.id, self.id
            )
            if not existing_resolution:
                unprocessed_references.append(ref)
        return unprocessed_references

    @abstractmethod
    def predict_referents(
        self, texts: t.List[str], references: t.List[t.List[t.Tuple[int, int]]]
    ) -> t.List[t.List[t.Tuple[str, str]]]:
        """
        Predict referents for multiple references across multiple documents.

        This abstract method must be implemented by child classes.

        Args:
            texts: List of document text strings
            references: List of lists of tuples containing (start, end) positions of references.
                       Each inner list corresponds to references in one document at the same index in texts.

        Returns:
            List of lists of tuples containing (gazetteer_name, identifier).
            Each inner list corresponds to referents for references in one document.
            Each tuple at position [i][j] is the referent for the reference at position [i][j] in the input.
            The gazetteer_name identifies which gazetteer the identifier refers to,
            and the identifier is the value used to identify the referent in that gazetteer.
        """
