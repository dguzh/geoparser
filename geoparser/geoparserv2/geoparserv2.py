import uuid
from typing import List, Optional, Union

from sqlmodel import Session

from geoparser.db.crud import DocumentRepository, ProjectRepository
from geoparser.db.db import engine
from geoparser.db.models import Document, DocumentCreate, Project, ProjectCreate
from geoparser.modules.recognizers.recognizer import Recognizer
from geoparser.modules.resolvers.resolver import Resolver
from geoparser.orchestrator import Orchestrator


class GeoparserV2:
    """
    User-facing interface for the geoparser functionality.

    Handles project management and orchestrates the recognition/resolution pipeline.
    The GeoparserV2 manages projects, documents, and determines what needs processing,
    while the Orchestrator handles the actual recognition/resolution execution.
    """

    def __init__(
        self,
        recognizer: Recognizer,
        resolver: Resolver,
        project_name: Optional[str] = None,
    ):
        """
        Initialize a GeoparserV2 instance.

        Args:
            recognizer: The recognizer module to use for identifying references.
            resolver: The resolver module to use for resolving references to referents.
            project_name: Optional name for persistent project storage.
                          If None, creates a temporary project.
        """
        # Project management
        self.project_name = project_name or f"temp_project_{uuid.uuid4()}"
        self.project_id = self._load_project(self.project_name)

        # Create orchestrator for this recognizer/resolver combination
        self.orchestrator = Orchestrator(recognizer, resolver)

    def _load_project(self, project_name: str) -> uuid.UUID:
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
                project = Project(name=project_create.name)
                project = ProjectRepository.create(db, project)

            return project.id

    def add_documents(self, texts: Union[str, List[str]]) -> List[uuid.UUID]:
        """
        Add documents to the project.

        Args:
            texts: Either a single document text or a list of document texts

        Returns:
            List of UUIDs of the created documents
        """
        # Convert single string to list for uniform processing
        if isinstance(texts, str):
            texts = [texts]

        with Session(engine) as db:
            document_ids = []
            for text in texts:
                document_create = DocumentCreate(text=text, project_id=self.project_id)
                document = DocumentRepository.create(db, document_create)
                document_ids.append(document.id)

            return document_ids

    def get_documents(
        self, document_ids: Optional[List[uuid.UUID]] = None
    ) -> List[Document]:
        """
        Retrieve documents with their associated references and referents,
        filtered by the configured recognizer and resolver.

        Args:
            document_ids: Optional list of specific document IDs to retrieve.
                          If None, retrieves all documents in the project.

        Returns:
            List of Document objects with filtered references and referents.
        """
        with Session(engine) as db:
            if document_ids:
                # Retrieve specific documents by their IDs
                documents = [
                    DocumentRepository.get(db, doc_id) for doc_id in document_ids
                ]
            else:
                # Retrieve all documents for the project
                documents = DocumentRepository.get_by_project(db, self.project_id)

            # Filter documents and their references/referents
            filtered_documents = []
            for doc in documents:
                if doc is not None:
                    # Filter references to only include those from our recognizer
                    filtered_references = [
                        ref
                        for ref in doc.references
                        if ref.recognizer_id == self.orchestrator.recognizer_id
                    ]

                    # For each reference, filter referents to only include those from our resolver
                    for ref in filtered_references:
                        filtered_referents = [
                            referent
                            for referent in ref.referents
                            if referent.resolver_id == self.orchestrator.resolver_id
                        ]
                        # Update the reference's referents list
                        ref.referents = filtered_referents

                    # Update the document's references list
                    doc.references = filtered_references
                    filtered_documents.append(doc)

            return filtered_documents

    def parse(self, texts: Union[str, List[str]]) -> List[Document]:
        """
        Parse one or more texts with the configured recognizer and resolver.

        This method adds documents to the project, processes them with
        the configured recognizer followed by the resolver, and returns
        the processed documents containing only results from this specific pipeline.

        Args:
            texts: Either a single document text or a list of texts

        Returns:
            List of Document objects with processed references and referents
            from the configured recognizer and resolver only.
        """

        # Add documents to the project and get their IDs
        document_ids = self.add_documents(texts)

        # Pass document IDs through the recognition pipeline
        self.orchestrator.run_recognizer(document_ids)

        # Pass document IDs through the resolution pipeline
        self.orchestrator.run_resolver(document_ids)

        # Return the parsed documents with fresh data from database
        return self.get_documents(document_ids)
