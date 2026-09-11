import typing as t
import uuid

from sqlmodel import Session

from geoparser.db.crud import (
    ReferentRepository,
    ResolutionRepository,
    ResolverRepository,
)
from geoparser.db.db import get_session
from geoparser.db.models import ReferentCreate, ResolutionCreate, ResolverCreate
from geoparser.gazetteer.gazetteer import Gazetteer

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
        with get_session() as session:
            resolver_record = ResolverRepository.get(session, id=resolver.id)
            if resolver_record is None:
                resolver_create = ResolverCreate(
                    id=resolver.id,
                    name=resolver.name,
                    config=resolver.config,
                )
                resolver_record = ResolverRepository.create(session, resolver_create)
            return resolver_record.id

    def predict(self, documents: list["Document"]) -> None:
        """
        Run the resolver on all references from the provided documents and store results in the database.

        Args:
            documents: List of Document objects containing references to process
        """
        # Ensure resolver record exists in database and get the ID
        resolver_id = self._ensure_resolver_record(self.resolver)

        if not documents:
            return

        with get_session() as session:
            texts, reference_boundaries, reference_objects = self._collect_unprocessed(
                session, documents, resolver_id
            )

            # Only call predict if there are documents with unprocessed references
            if not texts:
                return

            predicted_referents = self.resolver.predict(texts, reference_boundaries)

            # Record predictions for each document. Resolvers are pluggable, so
            # as in RecognitionService the prediction count is not enforced here.
            for unprocessed_references, doc_referents in zip(
                reference_objects,
                predicted_referents,
                strict=False,  # pragma: no mutate - leniency pinned by test
            ):
                self._record_referent_predictions(
                    session, unprocessed_references, doc_referents, resolver_id
                )

    def _collect_unprocessed(
        self,
        session: Session,
        documents: list["Document"],
        resolver_id: str,
    ) -> tuple[list[str], list[list[tuple[int, int]]], list[list["Reference"]]]:
        """
        Gather the documents that still have references this resolver has not seen.

        Args:
            session: Database session
            documents: Documents to inspect
            resolver_id: Resolver whose prior work should be skipped

        Returns:
            Parallel lists of document texts, reference spans, and the
            reference objects those spans came from
        """
        texts: list[str] = []
        boundaries: list[list[tuple[int, int]]] = []
        objects: list[list[Reference]] = []

        for doc in documents:
            unprocessed = self._filter_unprocessed_references(
                session, doc.references, resolver_id
            )
            if unprocessed:
                texts.append(doc.text)
                boundaries.append([(ref.start, ref.end) for ref in unprocessed])
                objects.append(unprocessed)

        return texts, boundaries, objects

    def fit(self, documents: list["Document"], **kwargs) -> None:
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
        # Resolvers are not required to be trainable, so `fit` is looked up
        # rather than declared on the base class.
        fit: t.Callable[..., None] | None = getattr(self.resolver, "fit", None)
        if fit is None:
            raise ValueError(
                f"Resolver '{self.resolver.name}' does not implement a fit method"
            )

        # Extract texts, references, and referents from documents
        texts = []
        references = []
        referents = []

        for doc in documents:
            doc_references, doc_referents = self._annotated_pairs(doc)

            # Only include documents that have referent annotations
            if doc_references:
                texts.append(doc.text)
                references.append(doc_references)
                referents.append(doc_referents)

        # Call the resolver's fit method with the prepared data
        fit(texts, references, referents, **kwargs)

    @staticmethod
    def _annotated_pairs(
        doc: "Document",
    ) -> tuple[list[tuple[int, int]], list[tuple[str, str]]]:
        """
        One document's resolved toponyms, as parallel spans and referents.

        ``doc.toponyms`` is already filtered by the recognizer context, and
        ``ref.location`` by the resolver context, so this keeps only the
        references that carry a referent from the resolver being trained.

        Args:
            doc: The document to read annotations from

        Returns:
            The reference spans and their (gazetteer, identifier) referents
        """
        annotated = [(ref, ref.location) for ref in doc.toponyms if ref.location]
        spans = [(ref.start, ref.end) for ref, _ in annotated]
        pairs = [
            (location.gazetteer_name, location.identifier) for _, location in annotated
        ]
        return spans, pairs

    def _record_referent_predictions(
        self,
        session: Session,
        unprocessed_references: list["Reference"],
        predicted_referents: list[tuple[str, str] | None],
        resolver_id: str,
    ) -> None:
        """
        Process referent predictions and update the database.

        Args:
            session: Database session
            unprocessed_references: List of references to process
            predicted_referents: List where each element is either a (gazetteer_name, identifier) tuple
                                or None for references where predictions are not available
            resolver_id: ID of the resolver that made the predictions
        """
        # Process each reference with its predicted referent; see above on
        # why a short prediction list is tolerated rather than rejected.
        for reference, referent in zip(
            unprocessed_references, predicted_referents, strict=False
        ):
            # Skip references where predictions are not available
            # (None indicates the resolver couldn't process this reference)
            if referent is None:
                continue

            # Create referent record for the single prediction with resolver ID
            gazetteer_name, identifier = referent
            self._create_referent_record(
                session, reference.id, gazetteer_name, identifier, resolver_id
            )

            # Mark reference as processed
            self._create_resolution_record(session, reference.id, resolver_id)

    def _create_referent_record(
        self,
        session: Session,
        reference_id: uuid.UUID,
        gazetteer_name: str,
        identifier: str,
        resolver_id: str,
    ) -> None:
        """
        Create a referent record with the resolver ID.

        Args:
            session: Database session
            reference_id: ID of the reference
            gazetteer_name: Name of the gazetteer
            identifier: Identifier value in the gazetteer
            resolver_id: ID of the resolver

        Raises:
            ValueError: If the feature does not exist in the gazetteer
        """
        # Validate that the feature exists in the installed gazetteer
        feature = Gazetteer(gazetteer_name).find(identifier)
        if feature is None:
            raise ValueError(
                f"Feature '{identifier}' does not exist in gazetteer '{gazetteer_name}'"
            )

        # Create the referent with resolver ID directly
        referent_create = ReferentCreate(
            reference_id=reference_id,
            gazetteer_name=gazetteer_name,
            feature_identifier=feature.identifier,
            resolver_id=resolver_id,
        )
        ReferentRepository.create(session, referent_create)

    def _create_resolution_record(
        self, session: Session, reference_id: uuid.UUID, resolver_id: str
    ) -> None:
        """
        Create a resolution record for a reference processed by a specific resolver.

        Args:
            session: Database session
            reference_id: ID of the reference that was processed
            resolver_id: ID of the resolver that processed it
        """
        resolution_create = ResolutionCreate(
            reference_id=reference_id, resolver_id=resolver_id
        )
        ResolutionRepository.create(session, resolution_create)

    def _filter_unprocessed_references(
        self, session: Session, references: list["Reference"], resolver_id: str
    ) -> list["Reference"]:
        """
        Filter out references that have already been processed by this resolver.

        Args:
            session: Database session
            references: List of references to check
            resolver_id: ID of the resolver to check for

        Returns:
            List of references that haven't been processed by this resolver.
        """
        unprocessed_references = []
        for ref in references:
            # Check if this reference has already been processed by this resolver
            existing_resolution = ResolutionRepository.get_by_reference_and_resolver(
                session, ref.id, resolver_id
            )
            if not existing_resolution:
                unprocessed_references.append(ref)
        return unprocessed_references
