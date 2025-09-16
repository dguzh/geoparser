import uuid
from typing import List, Union

from geoparser.db.models import Document
from geoparser.modules.recognizers import Recognizer
from geoparser.modules.resolvers import Resolver
from geoparser.project import Project


class GeoparserV2:
    """
    User-facing interface for the geoparser functionality.

    Provides a simple parse method for processing texts with configured recognizer and resolver.
    The GeoparserV2 creates a new project for each parse operation, making it stateless by default.
    """

    def __init__(
        self,
        recognizer: Recognizer,
        resolver: Resolver,
    ):
        """
        Initialize a GeoparserV2 instance.

        Args:
            recognizer: The recognizer module to use for identifying references.
            resolver: The resolver module to use for resolving references to referents.
        """
        self.recognizer = recognizer
        self.resolver = resolver

    def parse(self, texts: Union[str, List[str]], save: bool = False) -> List[Document]:
        """
        Parse one or more texts with the configured recognizer and resolver.

        This method creates a new project for each parse operation, processes the texts,
        and returns the results. By default, the project is deleted after processing
        to keep the parse method stateless.

        Args:
            texts: Either a single document text or a list of texts
            save: If True, preserve the project after processing. If False (default),
                  delete the project to maintain stateless behavior.

        Returns:
            List of Document objects with processed references and referents
            from the configured recognizer and resolver.
        """
        # Create a new project for this parse operation
        project_name = uuid.uuid4().hex[:8]
        project = Project(project_name)

        try:
            # Add documents to the project
            project.add_documents(texts)

            # Get all documents from the project (without filtering by recognizer/resolver)
            documents = project.get_documents()

            # Run the recognizer on all documents
            self.recognizer.run(documents)

            # Run the resolver on all documents
            self.resolver.run(documents)

            # Get all documents with results from our specific recognizer and resolver
            documents = project.get_documents(
                recognizer_id=self.recognizer.id,
                resolver_id=self.resolver.id,
            )

            # If save is True, inform the user about the project name
            if save:
                print(f"Results saved under project name: {project_name}")

            return documents

        finally:
            # Clean up the project unless the user wants to save it
            if not save:
                project.delete()
