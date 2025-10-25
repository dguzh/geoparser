import typing as t
import uuid
from typing import List, Tuple

from sqlmodel import Session

from geoparser.db.crud import (
    FeatureRepository,
    ReferentRepository,
    ResolutionRepository,
    ResolverRepository,
)
from geoparser.db.engine import get_engine
from geoparser.db.models import ReferentCreate, ResolutionCreate, ResolverCreate

if t.TYPE_CHECKING:
    from geoparser.db.models import Document, Reference
    from geoparser.modules.resolvers.base import Resolver


class ResolutionService:
    """
    Service layer that handles all database operations for reference resolution.

    This service acts as a bridge between resolver modules (which are DB-agnostic)
    and the database layer.
    """

    def __init__(self, resolver: "Resolver"):
        """
        Initialize the resolution service.

        Args:
            resolver: The resolver module to use for predictions
        """
        self.resolver = resolver

    def _ensure_resolver_record(self, resolver: "Resolver") -> str:
        """
        Ensure a resolver record exists in the database.

        Creates a new resolver record if it doesn't already exist.

        Args:
            resolver: The resolver module to ensure exists in the database

        Returns:
            The resolver ID from the database
        """
        with Session(get_engine()) as db:
            resolver_record = ResolverRepository.get(db, id=resolver.id)
            if resolver_record is None:
                resolver_create = ResolverCreate(
                    id=resolver.id,
                    name=resolver.name,
                    config=resolver.config,
                )
                resolver_record = ResolverRepository.create(db, resolver_create)
            return resolver_record.id

    def predict(self, documents: List["Document"]) -> None:
        """
        Run the resolver on all references from the provided documents and store results in the database.

        Args:
            documents: List of Document objects containing references to process
        """
        if not documents:
            return

        # Ensure resolver record exists in database and get the ID
        resolver_id = self._ensure_resolver_record(self.resolver)

        with Session(get_engine()) as db:
            # Collect data for prediction
            texts = []
            reference_boundaries = []
            reference_objects = []

            for doc in documents:
                # Filter to unprocessed references only
                unprocessed_references = self._filter_unprocessed_references(
                    db, doc.references, resolver_id
                )

                # Only add to lists if there are unprocessed references
                if unprocessed_references:
                    texts.append(doc.text)
                    reference_boundaries.append(
                        [(ref.start, ref.end) for ref in unprocessed_references]
                    )
                    reference_objects.append(unprocessed_references)

            # Only call predict if there are documents with unprocessed references
            if texts:
                # Get predictions from resolver using raw data
                predicted_referents = self.resolver.predict(texts, reference_boundaries)

                # Record predictions for each document
                for unprocessed_references, doc_referents in zip(
                    reference_objects, predicted_referents
                ):
                    self._record_referent_predictions(
                        db, unprocessed_references, doc_referents, resolver_id
                    )

    def fit(self, documents: List["Document"], **kwargs) -> None:
        """
        Train the resolver using the provided documents.

        This method prepares training data from documents that have reference and referent
        annotations and calls the resolver's fit method if it exists.

        Args:
            documents: List of Document objects with referent annotations for training
            **kwargs: Additional training parameters (e.g., output_path, epochs, batch_size)

        Raises:
            ValueError: If the resolver does not implement a fit method
        """
        # Check if the resolver has a fit method
        if not hasattr(self.resolver, "fit"):
            raise ValueError(
                f"Resolver '{self.resolver.name}' does not implement a fit method"
            )

        # Extract texts, references, and referents from documents
        texts = []
        references = []
        referents = []

        for doc in documents:
            # Filter references that have referents from this resolver
            # doc.toponyms returns references filtered by the recognizer context
            doc_references = []
            doc_referents = []

            for ref in doc.toponyms:
                # ref.location returns the feature filtered by the resolver context
                if ref.location:
                    doc_references.append((ref.start, ref.end))
                    doc_referents.append(
                        (
                            ref.location.source.gazetteer.name,
                            ref.location.location_id_value,
                        )
                    )

            # Only include documents that have referent annotations
            if doc_references:
                texts.append(doc.text)
                references.append(doc_references)
                referents.append(doc_referents)

        # Call the resolver's fit method with the prepared data
        self.resolver.fit(texts, references, referents, **kwargs)

    def _record_referent_predictions(
        self,
        db: Session,
        unprocessed_references: List["Reference"],
        predicted_referents: List[t.Union[Tuple[str, str], None]],
        resolver_id: uuid.UUID,
    ) -> None:
        """
        Process referent predictions and update the database.

        Args:
            db: Database session
            unprocessed_references: List of references to process
            predicted_referents: List where each element is either a (gazetteer_name, identifier) tuple
                                or None for references where predictions are not available
            resolver_id: ID of the resolver that made the predictions
        """
        # Process each reference with its predicted referent
        for reference, referent in zip(unprocessed_references, predicted_referents):
            # Skip references where predictions are not available
            # (None indicates the resolver couldn't process this reference)
            if referent is None:
                continue

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
        self, db: Session, references: List["Reference"], resolver_id: str
    ) -> List["Reference"]:
        """
        Filter out references that have already been processed by this resolver.

        Args:
            db: Database session
            references: List of references to check
            resolver_id: ID of the resolver to check for

        Returns:
            List of references that haven't been processed by this resolver.
        """
        unprocessed_references = []
        for ref in references:
            # Check if this reference has already been processed by this resolver
            existing_resolution = ResolutionRepository.get_by_reference_and_resolver(
                db, ref.id, resolver_id
            )
            if not existing_resolution:
                unprocessed_references.append(ref)
        return unprocessed_references
