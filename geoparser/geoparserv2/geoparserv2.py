from typing import List, Union

from geoparser.db.models import Document
from geoparser.modules.recognizers.recognizer import Recognizer
from geoparser.modules.resolvers.resolver import Resolver
from geoparser.project import Project


class GeoparserV2:
    """
    User-facing interface for the geoparser functionality.

    Provides a simple parse method for processing texts with configured recognizer and resolver.
    The GeoparserV2 uses a Project instance to manage documents and delegates processing
    to the recognizer and resolver modules directly.
    """

    def __init__(
        self,
        recognizer: Recognizer,
        resolver: Resolver,
        project_name: str = "default_project",
    ):
        """
        Initialize a GeoparserV2 instance.

        Args:
            recognizer: The recognizer module to use for identifying references.
            resolver: The resolver module to use for resolving references to referents.
            project_name: Name for persistent project storage.
        """
        self.recognizer = recognizer
        self.resolver = resolver
        self.project = Project(project_name)

    def parse(self, texts: Union[str, List[str]]) -> List[Document]:
        """
        Parse one or more texts with the configured recognizer and resolver.

        This method adds documents to the project, processes them with
        the configured recognizer and resolver, and returns the processed documents
        containing the results from these specific modules.

        Args:
            texts: Either a single document text or a list of texts

        Returns:
            List of Document objects with processed references and referents
            from the configured recognizer and resolver.
        """
        # Add documents to the project
        self.project.add_documents(texts)

        # Get all documents from the project (without filtering by recognizer/resolver)
        documents = self.project.get_documents()

        # Run the recognizer on all documents
        self.recognizer.run(documents)

        # Run the resolver on all documents
        self.resolver.run(documents)

        # Get all documents with results from our specific recognizer and resolver
        return self.project.get_documents(
            recognizer_id=self.recognizer.id,
            resolver_id=self.resolver.id,
        )
