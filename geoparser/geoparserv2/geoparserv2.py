from typing import List, Union

from geoparser.db.models import Document
from geoparser.pipeline import Pipeline
from geoparser.project import Project


class GeoparserV2:
    """
    User-facing interface for the geoparser functionality.

    Provides a simple parse method for processing texts with a configured pipeline.
    The GeoparserV2 uses a Project instance to manage documents and execute pipelines.
    """

    def __init__(self, pipeline: Pipeline, project_name: str = "default_project"):
        """
        Initialize a GeoparserV2 instance.

        Args:
            pipeline: The Pipeline object containing recognizer and resolver configuration.
            project_name: Name for persistent project storage.
        """
        self.pipeline = pipeline
        self.project = Project(project_name)

    def parse(self, texts: Union[str, List[str]]) -> List[Document]:
        """
        Parse one or more texts with the configured pipeline.

        This method adds documents to the project, processes them with
        the configured pipeline, and returns the processed documents
        containing the results from this specific pipeline.

        Args:
            texts: Either a single document text or a list of texts

        Returns:
            List of Document objects with processed references and referents
            from the configured pipeline.
        """
        # Add documents to the project
        self.project.add_documents(texts)

        # Run the recognizer on all documents in the project
        self.pipeline.run_recognizer(self.project)

        # Run the resolver on all documents in the project
        self.pipeline.run_resolver(self.project)

        # Get all documents with results from our specific pipeline
        return self.project.get_documents(
            recognizer_id=self.pipeline.recognizer_id,
            resolver_id=self.pipeline.resolver_id,
        )
