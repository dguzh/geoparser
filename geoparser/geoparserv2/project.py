import logging
import typing as t
import uuid
from typing import List, Union

from sqlmodel import Session

from geoparser.db.crud import DocumentRepository, ProjectRepository
from geoparser.db.db import get_db
from geoparser.db.models import Document, DocumentCreate, Project, ProjectCreate
from geoparser.geoparserv2.module_manager import ModuleManager
from geoparser.geoparserv2.modules import BaseModule


class GeoparserProject:
    """
    Main entry point for the project-level geoparser orchestration.

    This class provides a unified interface for project-level geoparsing operations
    including document management and module execution coordination.
    It delegates module-specific database interactions to the ModuleManager.
    """

    def __init__(self, project_name: str):
        """
        Initialize a GeoparserProject instance.

        Args:
            project_name: Project name. Will load or create a project with this name.
        """
        self.project_id = self._initialize_project(project_name)
        self.project_name = project_name

        # Create module manager for this project
        self.module_manager = ModuleManager(self.project_id)

    def _initialize_project(self, project_name: str) -> uuid.UUID:
        """
        Load an existing project or create a new one if it doesn't exist.

        Args:
            project_name: Name of the project to load or create

        Returns:
            Project ID that was loaded or created
        """
        db = next(get_db())
        project = self.load_project(db, project_name)

        if project is None:
            logging.info(
                f"No project found with name '{project_name}'; creating a new one."
            )
            project = self.create_project(db, project_name)

        return project.id

    def load_project(self, db: Session, project_name: str) -> t.Optional[Project]:
        """
        Load a project by name from the database.

        Args:
            db: Database session
            project_name: Name of the project to load

        Returns:
            Project if found, None otherwise
        """
        return ProjectRepository.get_by_name(db, project_name)

    def create_project(self, db: Session, project_name: str) -> Project:
        """
        Create a new project with the given name.

        Args:
            db: Database session
            project_name: Name for the new project

        Returns:
            Newly created Project object
        """
        project_create = ProjectCreate(name=project_name)
        project = Project(name=project_create.name)
        return ProjectRepository.create(db, project)

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

    def run(self, module: BaseModule) -> None:
        """
        Run a processing module on the current project.

        This method delegates the execution to the ModuleManager,
        which handles all module-specific database interactions.

        Args:
            module: The module instance to run.
        """
        # Delegate to module manager
        self.module_manager.run_module(module)

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
