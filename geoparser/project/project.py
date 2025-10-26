import json
import typing as t
import uuid
from pathlib import Path
from typing import List, Union

from geoparser.db.crud import DocumentRepository, ProjectRepository
from geoparser.db.db import get_session
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
        self.name = name
        self.id = self._ensure_project_record(name)

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
        self, texts: List[str], references: List[List[tuple]], label: str
    ) -> None:
        """
        Create references (toponym spans) using ManualRecognizer.

        Args:
            texts: List of document texts
            references: List of reference tuples (start, end) for each document
            label: Label to identify this recognition set
        """
        recognizer = ManualRecognizer(label=label, texts=texts, references=references)
        self.run_recognizer(recognizer)

    def create_referents(
        self,
        texts: List[str],
        references: List[List[tuple]],
        referents: List[List[tuple]],
        label: str,
    ) -> None:
        """
        Create referents (location assignments) using ManualResolver.

        Args:
            texts: List of document texts
            references: List of reference tuples (start, end) for each document
            referents: List of referent tuples (gazetteer_name, identifier) for each document
            label: Label to identify this resolution set
        """
        resolver = ManualResolver(
            label=label, texts=texts, references=references, referents=referents
        )
        self.run_resolver(resolver)

    def get_documents(
        self,
        recognizer_id: str = None,
        resolver_id: str = None,
    ) -> List[Document]:
        """
        Retrieve all documents in the project with context set for the specified recognizer/resolver.

        Args:
            recognizer_id: Recognizer ID to configure in document context for filtering references.
            resolver_id: Resolver ID to configure in reference context for filtering referents.

        Returns:
            List of Document objects with context set for filtering.
        """
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

    def run_recognizer(self, recognizer: "Recognizer") -> None:
        """
        Run a recognizer module on all documents in this project.

        This is a convenience method that simplifies the workflow for advanced users
        by handling service initialization and document retrieval internally.

        Args:
            recognizer: The recognizer module to run on all project documents
        """
        # Get all documents in the project
        documents = self.get_documents()

        # Initialize the recognition service with the recognizer
        recognition_service = RecognitionService(recognizer)

        # Run the recognizer on all documents
        recognition_service.predict(documents)

    def run_resolver(self, resolver: "Resolver") -> None:
        """
        Run a resolver module on all documents in this project.

        This is a convenience method that simplifies the workflow for advanced users
        by handling service initialization and document retrieval internally.

        Args:
            resolver: The resolver module to run on all project documents
        """
        # Get all documents in the project
        documents = self.get_documents()

        # Initialize the resolution service with the resolver
        resolution_service = ResolutionService(resolver)

        # Run the resolver on all documents
        resolution_service.predict(documents)

    def train_recognizer(
        self, recognizer: "Recognizer", recognizer_id: str, **kwargs
    ) -> None:
        """
        Train a recognizer module using documents with reference annotations from this project.

        This method retrieves documents that have been processed by a specific recognizer,
        prepares the training data, and calls the recognizer's fit method if available.

        Args:
            recognizer: The recognizer module to train
            recognizer_id: ID of the recognizer whose annotations to use for training
            **kwargs: Additional training parameters (e.g., output_path, epochs, batch_size)

        Raises:
            ValueError: If the recognizer does not implement a fit method
        """
        # Get all documents in the project with the specified recognizer context
        documents = self.get_documents(recognizer_id=recognizer_id)

        # Initialize the recognition service with the recognizer
        recognition_service = RecognitionService(recognizer)

        # Train the recognizer using the annotated documents
        recognition_service.fit(documents, **kwargs)

    def train_resolver(
        self, resolver: "Resolver", recognizer_id: str, resolver_id: str, **kwargs
    ) -> None:
        """
        Train a resolver module using documents with referent annotations from this project.

        This method retrieves documents that have been processed by specific recognizer and resolver,
        prepares the training data, and calls the resolver's fit method if available.

        Args:
            resolver: The resolver module to train
            recognizer_id: ID of the recognizer whose references to use
            resolver_id: ID of the resolver whose annotations to use for training
            **kwargs: Additional training parameters (e.g., output_path, epochs, batch_size)

        Raises:
            ValueError: If the resolver does not implement a fit method
        """
        # Get all documents in the project with the specified recognizer and resolver context
        documents = self.get_documents(
            recognizer_id=recognizer_id, resolver_id=resolver_id
        )

        # Initialize the resolution service with the resolver
        resolution_service = ResolutionService(resolver)

        # Train the resolver using the annotated documents
        resolution_service.fit(documents, **kwargs)

    def load_annotations(
        self, path: str, label: str = "annotator", create_documents: bool = False
    ) -> None:
        """
        Load annotations from an annotator JSON file and register them in the project.

        This method imports annotations from the legacy annotator format and registers
        them using ManualRecognizer for toponym spans and ManualResolver for location
        assignments. The annotations are stored with the provided label to distinguish
        different annotation sources.

        Args:
            path: Path to the JSON file exported from the annotator
            label: Label to identify this annotation set (default: "annotator")
                   This allows tracking multiple annotation sources separately
            create_documents: Whether to create new documents from the texts in the JSON
                             (default: False). Set to True if the documents don't exist yet,
                             False to add annotations to existing documents.

        Note:
            - Empty loc_id ("") indicates unannotated toponyms (skipped by resolver)
            - Null loc_id indicates toponyms annotated as having no location (skipped by resolver)
            - Non-empty loc_id values are registered as referents with the gazetteer
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
        self.create_references(texts, references, label)
        self.create_referents(texts, references, referents, label)

    def delete(self) -> None:
        """
        Delete this project and all its associated data from the database.

        This will remove the project, all its documents, references, referents,
        recognitions, and resolutions due to cascade delete relationships.
        """
        with get_session() as session:
            ProjectRepository.delete(session, id=self.id)
