import logging
import typing as t
import uuid
from typing import List, Union

from geoparser.db.crud import DocumentRepository, ProjectRepository
from geoparser.db.db import get_db
from geoparser.db.models import Document, DocumentCreate, Project, ProjectCreate
from geoparser.geoparserv2.module_interfaces import BaseModule
from geoparser.geoparserv2.module_runner import ModuleRunner


class GeoparserProject:
    """
    Main entry point for the project-level geoparser orchestration.

    This class provides a unified interface for project-level geoparsing operations
    including document management and module execution coordination.
    It delegates module-specific database interactions to the ModuleRunner.
    """

    def __init__(self, project_name: str):
        """
        Initialize a GeoparserProject instance.

        Args:
            project_name: Project name. Will load or create a project with this name.
        """
        self.project_id = self._initialize_project(project_name)
        self.project_name = project_name

        # Create module runner
        self.module_runner = ModuleRunner()

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

    def run(self, module: BaseModule) -> None:
        """
        Run a processing module on the current project.

        This method delegates the execution to the ModuleRunner,
        which handles all module-specific database interactions.

        Args:
            module: The module instance to run.
        """
        # Delegate to module runner with project_id
        self.module_runner.run_module(module, self.project_id)
