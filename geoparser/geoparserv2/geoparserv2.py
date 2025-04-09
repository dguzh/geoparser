import logging
import typing as t
import uuid
from typing import List, Optional, Union

from geoparser.db.crud import DocumentRepository, ProjectRepository
from geoparser.db.db import get_db
from geoparser.db.models import Document, DocumentCreate, Project, ProjectCreate
from geoparser.geoparserv2.orchestrator import Orchestrator
from geoparser.modules.interfaces import BaseModule


class GeoparserV2:
    """
    User-facing wrapper for the geoparser functionality.

    Provides a simple interface for geoparsing operations with optional
    project persistence and configurable processing modules.
    """

    def __init__(
        self,
        project_name: Optional[str] = None,
        pipeline: Optional[List[BaseModule]] = None,
    ):
        """
        Initialize a GeoparserV2 instance.

        Args:
            project_name: Optional name for persistent project storage.
                          If None, creates a temporary project.
            pipeline: List of processing modules for text processing pipeline.
        """
        # Project management
        self.project_name = project_name or f"temp_project_{uuid.uuid4()}"
        self.project_id = self._initialize_project(self.project_name)

        # Module management
        self.pipeline = pipeline or []
        self.orchestrator = Orchestrator()

    def _initialize_project(self, project_name: str) -> uuid.UUID:
        """
        Load an existing project or create a new one if it doesn't exist.

        Args:
            project_name: Name of the project to load or create

        Returns:
            Project ID that was loaded or created
        """
        db = next(get_db())

        # Try to load existing project
        project = ProjectRepository.get_by_name(db, project_name)

        # Create new project if it doesn't exist
        if project is None:
            logging.info(
                f"No project found with name '{project_name}'; creating a new one."
            )
            project_create = ProjectCreate(name=project_name)
            project = Project(name=project_create.name)
            project = ProjectRepository.create(db, project)

        return project.id

    def add_documents(self, texts: Union[str, List[str]]) -> List[uuid.UUID]:
        """
        Add one or more documents to the project.

        Args:
            texts: Either a single document text (str) or a list of document texts (List[str])

        Returns:
            List of UUIDs of the created documents
        """
        db = next(get_db())

        # Convert single string to list for uniform processing
        if isinstance(texts, str):
            texts = [texts]

        document_ids = []
        for text in texts:
            document_create = DocumentCreate(text=text, project_id=self.project_id)
            document = DocumentRepository.create(db, document_create)
            document_ids.append(document.id)

        return document_ids

    def get_documents(
        self, document_ids: t.Optional[List[uuid.UUID]] = None
    ) -> List[Document]:
        """
        Retrieve documents with their associated toponyms and locations.

        This method fetches document objects from the database along with their
        related toponyms and locations, enabling traversal like:
        documents[0].toponyms[0].locations[0]

        Args:
            document_ids: Optional list of document IDs to retrieve.
                          If None, retrieves all documents in the project.

        Returns:
            List of Document objects with related toponyms and locations.
        """
        db = next(get_db())

        if document_ids:
            # Retrieve specific documents by their IDs
            documents = [DocumentRepository.get(db, doc_id) for doc_id in document_ids]
        else:
            # Retrieve all documents for the project
            documents = DocumentRepository.get_by_project(db, self.project_id)

        return documents

    def run_module(self, module: BaseModule) -> None:
        """
        Run a single processing module on the project's documents.

        Args:
            module: The processing module to run.
        """
        self.orchestrator.run_module(module, self.project_id)

    def run_pipeline(self) -> None:
        """
        Run all modules in the pipeline on the project's documents.

        This executes each module in the pipeline in sequence.
        """
        for module in self.pipeline:
            self.run_module(module)

    def parse(self, texts: Union[str, List[str]]) -> List[Document]:
        """
        Parse one or more texts with the configured pipeline.

        This method adds documents to the project, processes them with
        all configured modules in the pipeline, and returns the processed documents.

        Args:
            texts: Either a single document text or a list of texts

        Returns:
            List of Document objects with processed toponyms and locations
        """
        # Add documents to the project and get their IDs
        document_ids = self.add_documents(texts)

        # Run the pipeline on the project
        self.run_pipeline()

        # Retrieve the processed documents using the project
        return self.get_documents(document_ids)
