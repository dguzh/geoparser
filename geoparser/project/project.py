import json
import typing as t
import uuid
from pathlib import Path
from typing import List, Union

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

    def create_documents(self, texts: Union[str, List[str]]) -> None:
        """
        Create documents in the project.

        Args:
            texts: Either a single document text or a list of document texts
        """
        # Convert single string to list for uniform processing
        if isinstance(texts, str):
            texts = [texts]

        with get_session() as session:
            for text in texts:
                document_create = DocumentCreate(text=text, project_id=self.id)
                DocumentRepository.create(session, document_create)

    def create_references(
        self, texts: List[str], references: List[List[tuple]], tag: str
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
        texts: List[str],
        references: List[List[tuple]],
        referents: List[List[tuple]],
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

    def get_documents(self, tag: str = "latest") -> List[Document]:
        """
        Retrieve all documents in the project with context set for the specified tag.

        Args:
            tag: Tag identifier to determine which recognizer/resolver context to use
                 (default: "latest")

        Returns:
            List of Document objects with context set for filtering.
        """
        # Retrieve recognizer and resolver IDs for the specified tag
        recognizer_id = self.context.get_recognizer_context(tag)
        resolver_id = self.context.get_resolver_context(tag)

        with get_session() as session:
            # Retrieve all documents for the project
            documents = DocumentRepository.get_by_project(session, self.id)

            # Always set context on each document (even if None)
            for doc in documents:
                doc._set_recognizer_context(recognizer_id)

                # Always set context on each reference (even if None)
                for ref in doc.references:
                    ref._set_resolver_context(resolver_id)

            return documents

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
        path = Path(path)
        with open(path, "r") as f:
            data = json.load(f)

        # Extract gazetteer name from annotations
        gazetteer_name = data["gazetteer"]

        # Prepare aligned lists for ManualRecognizer and ManualResolver
        texts = []
        references = []  # All toponyms for both recognizer and resolver
        referents = []  # Location assignments (with None for non-geocoded toponyms)

        for doc in data["documents"]:
            text = doc["text"]
            texts.append(text)

            # Extract all toponyms as references
            doc_references = [(t["start"], t["end"]) for t in doc["toponyms"]]
            references.append(doc_references)

            # Create referents list aligned with ALL references
            # Use None for toponyms that are not geocoded
            doc_referents = []
            for toponym in doc["toponyms"]:
                # Only include toponyms that have been geocoded (loc_id is not "" and not null)
                if toponym["loc_id"] and toponym["loc_id"] != "":
                    doc_referents.append((gazetteer_name, toponym["loc_id"]))
                else:
                    # Non-geocoded: use None so resolver skips it
                    doc_referents.append(None)

            referents.append(doc_referents)

        # Create documents in the project if requested
        if create_documents:
            self.create_documents(texts)

        # Create references and referents using the extracted methods
        self.create_references(texts, references, tag)
        self.create_referents(texts, references, referents, tag)

    def delete(self) -> None:
        """
        Delete this project and all its associated data from the database.

        This will remove the project, all its documents, references, referents,
        recognitions, and resolutions due to cascade delete relationships.
        """
        with get_session() as session:
            ProjectRepository.delete(session, id=self.id)
