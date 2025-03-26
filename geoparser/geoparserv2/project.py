import logging
import typing as t
import uuid
from typing import List, Union

from sqlmodel import Session

from geoparser.db.crud import DocumentRepository, ProjectRepository
from geoparser.db.db import get_db
from geoparser.db.models import DocumentCreate, Project, ProjectCreate
from geoparser.geoparserv2.modules import BaseModule


class GeoparserProject:
    """
    Main entry point for the project-level geoparser orchestration.

    This class provides a unified interface for project-level geoparsing operations
    including document management, toponym recognition, and resolution.
    It serves as the orchestrator for all project-related tasks.
    """

    def __init__(self, project_name: str):
        """
        Initialize a GeoparserProject instance.

        Args:
            project_name: Project name. Will load or create a project with this name.
        """
        self.project_id = self._initialize_project(project_name)
        self.project_name = project_name

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

        This method will execute the specified module, which can be either
        a recognition module or a resolution module.

        Args:
            module: The module instance to run.
        """
        # Run the module on the project ID
        module.run(self.project_id)

    def get_documents(self) -> list[dict]:
        """
        Retrieve all documents in the current project.

        Returns:
            List of document dictionaries with id and text.
        """
        # Implementation for retrieving documents

    def get_toponyms(self, recognition_module_name: str) -> list[dict]:
        """
        Get toponyms recognized by a specific recognition module.

        Args:
            recognition_module_name: Name of the recognition module.

        Returns:
            List of toponym dictionaries with relevant information.
        """
        # Implementation for retrieving toponyms

    def get_locations(
        self, recognition_module_name: str, resolution_module_name: str
    ) -> list[dict]:
        """
        Get locations resolved by a specific combination of recognition and resolution modules.

        Args:
            recognition_module_name: Name of the recognition module that produced the toponyms.
            resolution_module_name: Name of the resolution module that resolved the locations.

        Returns:
            List of location dictionaries with relevant information.
        """
        # Implementation for retrieving locations
