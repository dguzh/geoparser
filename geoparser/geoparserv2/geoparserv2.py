import logging
import typing as t
import uuid
from typing import List, Optional, Union

from geoparser.db.crud import DocumentRepository, ProjectRepository
from geoparser.db.db import get_db
from geoparser.db.models import (
    Document,
    DocumentCreate,
    DocumentRead,
    Location,
    LocationRead,
    Project,
    ProjectCreate,
    RecognitionModuleRead,
    ResolutionModuleRead,
    Toponym,
    ToponymRead,
)
from geoparser.geoparserv2.orchestrator import Orchestrator
from geoparser.modules.interfaces import AbstractModule


class GeoparserV2:
    """
    User-facing wrapper for the geoparser functionality.

    Provides a simple interface for geoparsing operations with optional
    project persistence and configurable processing modules.
    """

    def __init__(
        self,
        project_name: Optional[str] = None,
        pipeline: Optional[List[AbstractModule]] = None,
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
    ) -> List[DocumentRead]:
        """
        Retrieve documents with their associated toponyms and locations.

        This method fetches document objects from the database along with their
        related toponyms and locations, enabling traversal like:
        documents[0].toponyms[0].locations[0]

        Args:
            document_ids: Optional list of document IDs to retrieve.
                          If None, retrieves all documents in the project.

        Returns:
            List of DocumentRead objects with related toponyms and locations.
        """
        db = next(get_db())

        if document_ids:
            # Retrieve specific documents by their IDs
            documents = [DocumentRepository.get(db, doc_id) for doc_id in document_ids]
        else:
            # Retrieve all documents for the project
            documents = DocumentRepository.get_by_project(db, self.project_id)

        # Convert ORM objects to read models
        return [self._convert_to_document_read(doc) for doc in documents]

    def _convert_to_document_read(self, document: "Document") -> DocumentRead:
        """
        Convert a Document ORM object to a DocumentRead model, including all related objects.

        Args:
            document: The Document ORM object to convert

        Returns:
            A DocumentRead object with nested ToponymRead and LocationRead objects
        """
        doc_read = DocumentRead.model_validate(document)
        doc_read.toponyms = [
            self._convert_to_toponym_read(toponym) for toponym in document.toponyms
        ]
        return doc_read

    def _convert_to_toponym_read(self, toponym: "Toponym") -> ToponymRead:
        """
        Convert a Toponym ORM object to a ToponymRead model, including all related objects.

        Args:
            toponym: The Toponym ORM object to convert

        Returns:
            A ToponymRead object with nested LocationRead objects
        """
        toponym_read = ToponymRead.model_validate(toponym)

        toponym_read.locations = [
            self._convert_to_location_read(location) for location in toponym.locations
        ]

        toponym_read.modules = [
            RecognitionModuleRead.model_validate(recog_obj.module)
            for recog_obj in toponym.recognition_objects
        ]

        return toponym_read

    def _convert_to_location_read(self, location: "Location") -> LocationRead:
        """
        Convert a Location ORM object to a LocationRead model, including all related objects.

        Args:
            location: The Location ORM object to convert

        Returns:
            A LocationRead object with related module information
        """
        location_read = LocationRead.model_validate(location)

        # Extract and convert the modules from resolution_objects
        location_read.modules = [
            ResolutionModuleRead.model_validate(resol_obj.module)
            for resol_obj in location.resolution_objects
        ]

        return location_read

    def run_module(self, module: AbstractModule) -> None:
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

    def parse(self, texts: Union[str, List[str]]) -> List[DocumentRead]:
        """
        Parse one or more texts with the configured pipeline.

        This method adds documents to the project, processes them with
        all configured modules in the pipeline, and returns the processed documents.

        Args:
            texts: Either a single document text or a list of texts

        Returns:
            List of DocumentRead objects with processed toponyms and locations
        """
        # Add documents to the project and get their IDs
        document_ids = self.add_documents(texts)

        # Run the pipeline on the project
        self.run_pipeline()

        # Retrieve the processed documents using the project
        return self.get_documents(document_ids)
