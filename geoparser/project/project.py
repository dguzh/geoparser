import json
import typing as t
import uuid
from pathlib import Path

from sqlmodel import Session

from geoparser.context import Context
from geoparser.db.crud import DocumentRepository, ProjectRepository
from geoparser.db.db import create_db_and_tables, get_session
from geoparser.db.models import Document, DocumentCreate, ProjectCreate
from geoparser.modules.recognizers.manual import ManualRecognizer
from geoparser.modules.resolvers.manual import ManualResolver
from geoparser.services.recognition import RecognitionService
from geoparser.services.resolution import ResolutionService

if t.TYPE_CHECKING:
    from geoparser.modules.recognizers import Recognizer
    from geoparser.modules.resolvers import Resolver


class Project:
    """
    Handles project management and pipeline execution.

    This class manages project lifecycle, document management, and provides
    methods to run processing pipelines on project documents.
    """

    def __init__(self, name: str):
        """
        Initialize a Project instance.

        Args:
            name: Name for the project. If the project doesn't exist,
                  it will be created.
        """
        # Ensure database tables exist
        create_db_and_tables()

        self.name = name
        self.id = self._ensure_project_record(name)
        self.context = Context(project_id=self.id)

    def _ensure_project_record(self, name: str) -> uuid.UUID:
        """
        Ensure a project record exists in the database.

        Creates a new project record if it doesn't already exist.

        Args:
            name: Name of the project to load or create

        Returns:
            Project ID from the database
        """
        with get_session() as session:
            # Try to load existing project
            project_record = ProjectRepository.get_by_name(session, name)

            # Create new project if it doesn't exist
            if project_record is None:
                project_create = ProjectCreate(name=name)
                project_record = ProjectRepository.create(session, project_create)

            return project_record.id

    def create_documents(self, texts: t.Sequence[str]) -> list[uuid.UUID]:
        """
        Create documents in the project.

        The returned IDs are in the same order as the texts that were passed in,
        which lets you relate documents back to whatever they came from. Keep
        them alongside your own records and pass them to :meth:`get_documents`
        to retrieve results for specific documents later on.

        Args:
            texts: Document texts to create. A single document is created by
                   passing a sequence with one text in it.

        Returns:
            IDs of the created documents, in the order the texts were provided

        Raises:
            TypeError: If a single text is passed instead of a sequence of texts
        """
        # A bare string would be iterated character by character, creating one
        # document per character, so reject it instead of doing that silently
        if isinstance(texts, str):
            # pragma: no mutate start - the wording of this guidance is not
            # behaviour; a test pins the type and that it names the method.
            raise TypeError(
                "create_documents() expects a sequence of texts. To create a single "
                "document, pass a sequence with one text in it: "
                "create_documents(['...'])."
            )
            # pragma: no mutate end

        document_ids = []

        with get_session() as session:
            for text in texts:
                document_create = DocumentCreate(text=text, project_id=self.id)
                document = DocumentRepository.create(session, document_create)
                document_ids.append(document.id)

        return document_ids

    def create_references(
        self, texts: list[str], references: list[list[tuple]], tag: str
    ) -> None:
        """
        Create references (toponym spans) using ManualRecognizer.

        Args:
            texts: List of document texts
            references: List of reference tuples (start, end) for each document
            tag: Tag to identify this recognition set
        """
        recognizer = ManualRecognizer(label=tag, texts=texts, references=references)
        self.run_recognizer(recognizer, tag=tag)

    def create_referents(
        self,
        texts: list[str],
        references: list[list[tuple]],
        referents: list[list[tuple | None]],
        tag: str,
    ) -> None:
        """
        Create referents (location assignments) using ManualResolver.

        Args:
            texts: List of document texts
            references: List of reference tuples (start, end) for each document
            referents: List of referent tuples (gazetteer_name, identifier) for each document
            tag: Tag to identify this resolution set
        """
        resolver = ManualResolver(
            label=tag, texts=texts, references=references, referents=referents
        )
        self.run_resolver(resolver, tag=tag)

    @staticmethod
    def _normalize_document_ids(
        ids: uuid.UUID | str | t.Sequence[uuid.UUID | str],
    ) -> list[uuid.UUID]:
        """
        Convert document IDs given as UUIDs or strings into a list of UUIDs.

        Args:
            ids: A single document ID or a sequence of document IDs

        Returns:
            List of document IDs as UUID objects

        Raises:
            ValueError: If a value cannot be interpreted as a document ID
        """
        # A single ID is accepted as well as a sequence of them
        if isinstance(ids, (str, uuid.UUID)):
            ids = [ids]

        normalized = []
        for value in ids:
            if isinstance(value, uuid.UUID):
                normalized.append(value)
                continue
            try:
                normalized.append(uuid.UUID(str(value)))
            except (AttributeError, TypeError, ValueError):
                # pragma: no mutate start - wording only; a test pins the type
                # and that the message names create_documents().
                raise ValueError(
                    f"'{value}' is not a valid document ID. Document IDs are the values "
                    "returned by create_documents(). To select results by tag instead, "
                    "pass the tag as a keyword argument: get_documents(tag='...')."
                ) from None
                # pragma: no mutate end

        return normalized

    def get_documents(
        self,
        ids: uuid.UUID | str | t.Sequence[uuid.UUID | str] | None = None,
        tag: str = "latest",
    ) -> list[Document]:
        """
        Retrieve documents in the project with context set for the specified tag.

        Args:
            ids: Document IDs to retrieve, as returned by :meth:`create_documents`.
                 The documents are returned in the order given here. If omitted,
                 every document in the project is returned.
            tag: Tag identifier to determine which recognizer/resolver context to use
                 (default: "latest")

        Returns:
            List of Document objects with context set for filtering.

        Raises:
            ValueError: If an ID does not belong to a document in this project
        """
        # Validate the requested IDs before touching the database
        requested_ids = None if ids is None else self._normalize_document_ids(ids)

        # Retrieve recognizer and resolver IDs for the specified tag
        recognizer_id = self.context.get_recognizer_context(tag)
        resolver_id = self.context.get_resolver_context(tag)

        with get_session() as session:
            if requested_ids is None:
                # Retrieve all documents for the project
                documents = DocumentRepository.get_by_project(session, self.id)
            else:
                documents = self._fetch_documents_in_order(session, requested_ids)

            self._apply_context(documents, recognizer_id, resolver_id)
            return documents

    def _fetch_documents_in_order(
        self, session: Session, requested_ids: list[uuid.UUID]
    ) -> list[Document]:
        """
        Retrieve specific documents, in the order they were requested.

        Args:
            session: Database session
            requested_ids: Document IDs, already normalized

        Returns:
            The documents, ordered to match requested_ids

        Raises:
            ValueError: If an ID does not belong to a document in this project
        """
        found = {
            document.id: document
            for document in DocumentRepository.get_by_ids(
                session, self.id, requested_ids
            )
        }

        self._reject_unknown_ids(requested_ids, found)
        return [found[id] for id in requested_ids]

    def _reject_unknown_ids(
        self, requested_ids: list[uuid.UUID], found: dict[uuid.UUID, Document]
    ) -> None:
        """
        Fail if any requested ID is not a document in this project.

        Args:
            requested_ids: The IDs that were asked for
            found: The documents that were actually retrieved, keyed by ID

        Raises:
            ValueError: If any requested ID is missing
        """
        missing = [str(id) for id in requested_ids if id not in found]
        if missing:
            raise ValueError(
                f"No documents with the following IDs exist in project "
                f"'{self.name}': {', '.join(missing)}"
            )

    @staticmethod
    def _apply_context(
        documents: list[Document],
        recognizer_id: str | None,
        resolver_id: str | None,
    ) -> None:
        """
        Point each document and reference at one tag's recognizer and resolver.

        The context is always set, including to None, so that a document loaded
        for a tag with no results filters to nothing rather than to everything.

        Args:
            documents: Documents to annotate in place
            recognizer_id: Recognizer whose references should be visible
            resolver_id: Resolver whose referents should be visible
        """
        for doc in documents:
            doc._set_recognizer_context(recognizer_id)
            for ref in doc.references:
                ref._set_resolver_context(resolver_id)

    def run_recognizer(self, recognizer: "Recognizer", tag: str = "latest") -> None:
        """
        Run a recognizer module on all documents in this project.

        This is a convenience method that simplifies the workflow for advanced users
        by handling service initialization and document retrieval internally.

        Args:
            recognizer: The recognizer module to run on all project documents
            tag: Tag to associate with this recognizer run (default: "latest")
        """
        # Get all documents in the project
        documents = self.get_documents()

        # Initialize the recognition service with the recognizer
        recognition_service = RecognitionService(recognizer)

        # Run the recognizer on all documents
        recognition_service.predict(documents)

        # Update the context with this recognizer for the specified tag
        self.context.update_recognizer_context(tag, recognizer.id)

    def run_resolver(self, resolver: "Resolver", tag: str = "latest") -> None:
        """
        Run a resolver module on all documents in this project.

        This is a convenience method that simplifies the workflow for advanced users
        by handling service initialization and document retrieval internally.

        Args:
            resolver: The resolver module to run on all project documents
            tag: Tag to associate with this resolver run (default: "latest")
        """
        # Get all documents in the project
        documents = self.get_documents()

        # Initialize the resolution service with the resolver
        resolution_service = ResolutionService(resolver)

        # Run the resolver on all documents
        resolution_service.predict(documents)

        # Update the context with this resolver for the specified tag
        self.context.update_resolver_context(tag, resolver.id)

    def train_recognizer(self, recognizer: "Recognizer", tag: str, **kwargs) -> None:
        """
        Train a recognizer module using documents with reference annotations from this project.

        This method retrieves documents that have been processed by a specific recognizer,
        prepares the training data, and calls the recognizer's fit method if available.

        Args:
            recognizer: The recognizer module to train
            tag: Tag identifying which annotations to use for training
            **kwargs: Additional training parameters (e.g., output_path, epochs, batch_size)

        Raises:
            ValueError: If the recognizer does not implement a fit method
        """
        # Get all documents in the project with the specified tag context
        documents = self.get_documents(tag=tag)

        # Initialize the recognition service with the recognizer
        recognition_service = RecognitionService(recognizer)

        # Train the recognizer using the annotated documents
        recognition_service.fit(documents, **kwargs)

    def train_resolver(self, resolver: "Resolver", tag: str, **kwargs) -> None:
        """
        Train a resolver module using documents with referent annotations from this project.

        This method retrieves documents that have been processed by specific recognizer and resolver,
        prepares the training data, and calls the resolver's fit method if available.

        Args:
            resolver: The resolver module to train
            tag: Tag identifying which annotations to use for training
            **kwargs: Additional training parameters (e.g., output_path, epochs, batch_size)

        Raises:
            ValueError: If the resolver does not implement a fit method
        """
        # Get all documents in the project with the specified tag context
        documents = self.get_documents(tag=tag)

        # Initialize the resolution service with the resolver
        resolution_service = ResolutionService(resolver)

        # Train the resolver using the annotated documents
        resolution_service.fit(documents, **kwargs)

    def load_annotations(
        self, path: str, tag: str, create_documents: bool = False
    ) -> None:
        """
        Load annotations from an annotator JSON file and register them in the project.

        This method imports annotations from the legacy annotator format and registers
        them using ManualRecognizer for toponym spans and ManualResolver for location
        assignments. The annotations are stored with the provided tag to distinguish
        different annotation sources.

        Args:
            path: Path to the JSON file exported from the annotator
            tag: Tag to identify this annotation set
                 This allows tracking multiple annotation sources separately
            create_documents: Whether to create new documents from the texts in the JSON
                             (default: False). Set to True if the documents don't exist yet,
                             False to add annotations to existing documents.
        """
        # Load JSON file
        file_path = Path(path)
        with open(file_path) as f:
            data = json.load(f)

        # Extract gazetteer name from annotations
        gazetteer_name = data["gazetteer"]

        # Prepare aligned lists for ManualRecognizer and ManualResolver
        texts = []
        references = []  # All toponyms for both recognizer and resolver
        referents = []  # Location assignments (with None for non-geocoded toponyms)

        for doc in data["documents"]:
            texts.append(doc["text"])
            references.append([(t["start"], t["end"]) for t in doc["toponyms"]])
            referents.append(self._referents_for(doc["toponyms"], gazetteer_name))

        # Create documents in the project if requested
        if create_documents:
            self.create_documents(texts)

        # Create references and referents using the extracted methods
        self.create_references(texts, references, tag)
        self.create_referents(texts, references, referents, tag)

    @staticmethod
    def _referents_for(
        toponyms: list[dict], gazetteer_name: str
    ) -> list[tuple[str, str] | None]:
        """
        Build a referent per toponym, aligned one-to-one with the references.

        Args:
            toponyms: Toponym records from an annotator export
            gazetteer_name: Gazetteer the loc_ids belong to

        Returns:
            One entry per toponym: a (gazetteer, identifier) pair when it was
            geocoded, otherwise None so the resolver skips it.
        """
        return [
            (gazetteer_name, toponym["loc_id"]) if toponym["loc_id"] else None
            for toponym in toponyms
        ]

    def delete(self) -> None:
        """
        Delete this project and all its associated data from the database.

        This will remove the project, all its documents, references, referents,
        recognitions, and resolutions due to cascade delete relationships.
        """
        with get_session() as session:
            ProjectRepository.delete(session, id=self.id)
