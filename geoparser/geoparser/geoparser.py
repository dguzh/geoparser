import uuid
from typing import List, Optional, Union

from geoparser.db.models import Document
from geoparser.modules.recognizers import Recognizer
from geoparser.modules.resolvers import Resolver
from geoparser.project import Project


class Geoparser:
    """
    User-facing interface for the geoparser functionality.

    Provides a simple parse method for processing texts with configured recognizer and resolver.
    The Geoparser creates a new project for each parse operation, making it stateless by default.

    The recognizer and resolver have to be provided explicitly, so that it is
    always clear which modules a pipeline is built from::

        from geoparser import Geoparser
        from geoparser.modules import SentenceTransformerResolver, SpacyRecognizer

        geoparser = Geoparser(
            recognizer=SpacyRecognizer(),
            resolver=SentenceTransformerResolver(gazetteer_name="geonames"),
        )
    """

    def __init__(
        self,
        recognizer: Optional[Recognizer],
        resolver: Optional[Resolver],
    ):
        """
        Initialize a Geoparser instance.

        Args:
            recognizer: The recognizer module to use for identifying references,
                        or None to skip the recognition step.
            resolver: The resolver module to use for resolving references to referents,
                      or None to skip the resolution step.
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
            from the configured recognizer and resolver, in the same order as
            the texts that were passed in.
        """
        # Create a new project for this parse operation
        project_name = uuid.uuid4().hex[:8]
        project = Project(project_name)

        try:
            # Create documents in the project
            document_ids = project.create_documents(texts)

            # Run the recognizer on all documents (if provided)
            if self.recognizer is not None:
                project.run_recognizer(self.recognizer)

            # Run the resolver on all documents (if provided)
            if self.resolver is not None:
                project.run_resolver(self.resolver)

            # Get the documents back in input order, with results from our
            # specific recognizer and resolver
            documents = project.get_documents(ids=document_ids)

            # If save is True, inform the user about the project name
            if save:
                print(f"Results saved under project name: {project_name}")

            return documents

        finally:
            # Clean up the project unless the user wants to save it
            if not save:
                project.delete()
