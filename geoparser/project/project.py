import uuid
from typing import List, Union

from sqlmodel import Session

from geoparser.db.crud import DocumentRepository, ProjectRepository
from geoparser.db.db import engine
from geoparser.db.models import Document, DocumentCreate, ProjectCreate


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
        Retrieve all documents in the project with their associated references and referents,
        filtered by the specified recognizer and resolver.

        Args:
            recognizer_id: Recognizer ID to filter references by. If None, no references returned. Defaults to None.
            resolver_id: Resolver ID to filter referents by. If None, no referents returned. Defaults to None.

        Returns:
            List of Document objects with filtered references and referents.
        """
        with Session(engine) as db:
            # Retrieve all documents for the project
            documents = DocumentRepository.get_by_project(db, self.id)

            # Filter documents and their references/referents
            filtered_documents = []
            for doc in documents:
                # Filter references by recognizer (empty list if recognizer_id is None)
                if recognizer_id is not None:
                    filtered_references = [
                        ref
                        for ref in doc.references
                        if ref.recognizer_id == recognizer_id
                    ]
                else:
                    filtered_references = []

                # Filter referents by resolver (only if there are references and resolver_id is provided)
                if resolver_id is not None and filtered_references:
                    for ref in filtered_references:
                        filtered_referents = [
                            referent
                            for referent in ref.referents
                            if referent.resolver_id == resolver_id
                        ]
                        ref.referents = filtered_referents
                else:
                    # Set empty referents for all references if resolver_id is None or no references
                    for ref in filtered_references:
                        ref.referents = []

                # Update the document's references list
                doc.references = filtered_references
                filtered_documents.append(doc)

            return filtered_documents
