import typing as t
import uuid
from typing import List, Union

from sqlmodel import Session

from geoparser.db.crud import DocumentRepository, ProjectRepository
from geoparser.db.engine import engine
from geoparser.db.models import Document, DocumentCreate, ProjectCreate
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

    def __init__(self, project_name: str):
        """
        Initialize a Project instance.

        Args:
            project_name: Name for the project. If the project doesn't exist,
                         it will be created.
        """
        self.project_name = project_name
        self.id = self._load(project_name)

    def _load(self, project_name: str) -> uuid.UUID:
        """
        Load an existing project or create a new one if it doesn't exist.

        Args:
            project_name: Name of the project to load or create

        Returns:
            Project ID that was loaded or created
        """
        with Session(engine) as db:
            # Try to load existing project
            project = ProjectRepository.get_by_name(db, project_name)

            # Create new project if it doesn't exist
            if project is None:
                project_create = ProjectCreate(name=project_name)
                project = ProjectRepository.create(db, project_create)

            return project.id

    def add_documents(self, texts: Union[str, List[str]]) -> None:
        """
        Add documents to the project.

        Args:
            texts: Either a single document text or a list of document texts
        """
        # Convert single string to list for uniform processing
        if isinstance(texts, str):
            texts = [texts]

        with Session(engine) as db:
            for text in texts:
                document_create = DocumentCreate(text=text, project_id=self.id)
                DocumentRepository.create(db, document_create)

    def get_documents(
        self,
        recognizer_id: uuid.UUID = None,
        resolver_id: uuid.UUID = None,
    ) -> List[Document]:
        """
        Retrieve all documents in the project with context set for the specified recognizer/resolver.

        Args:
            recognizer_id: Recognizer ID to configure in document context for filtering references.
            resolver_id: Resolver ID to configure in reference context for filtering referents.

        Returns:
            List of Document objects with context set for filtering.
        """
        with Session(engine, expire_on_commit=False) as db:
            # Retrieve all documents for the project
            documents = DocumentRepository.get_by_project(db, self.id)

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
        recognition_service.run(documents)

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
        resolution_service.run(documents)

    def delete(self) -> None:
        """
        Delete this project and all its associated data from the database.

        This will remove the project, all its documents, references, referents,
        recognitions, and resolutions due to cascade delete relationships.
        """
        with Session(engine) as db:
            ProjectRepository.delete(db, id=self.id)
