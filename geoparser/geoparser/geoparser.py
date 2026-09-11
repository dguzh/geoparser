import uuid
from collections.abc import Sequence
from typing import overload

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
        from geoparser.modules import GLiNER2Recognizer, JinaResolver

        geoparser = Geoparser(
            recognizer=GLiNER2Recognizer(),
            resolver=JinaResolver(gazetteer_name="geonames"),
        )
    """

    def __init__(
        self,
        recognizer: Recognizer | None,
        resolver: Resolver | None,
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

    def _run_modules(self, project: Project) -> None:
        """
        Run whichever of the two modules were configured.

        Args:
            project: The project holding the documents to process
        """
        if self.recognizer is not None:
            project.run_recognizer(self.recognizer)
        if self.resolver is not None:
            project.run_resolver(self.resolver)

    @overload
    def parse(self, texts: str, save: bool = False) -> Document: ...

    @overload
    def parse(self, texts: Sequence[str], save: bool = False) -> list[Document]: ...

    def parse(
        self, texts: str | Sequence[str], save: bool = False
    ) -> Document | list[Document]:
        """
        Parse one or more texts with the configured recognizer and resolver.

        The result mirrors the input: a single text is parsed into a single
        document, while a sequence of texts is parsed into a list of documents
        in the same order as the texts that were passed in.

        This method creates a new project for each parse operation, processes the texts,
        and returns the results. By default, the project is deleted after processing
        to keep the parse method stateless.

        Args:
            texts: Either a single document text or a sequence of texts
            save: If True, preserve the project after processing. If False (default),
                  delete the project to maintain stateless behavior.

        Returns:
            A single Document if a single text was passed, or a list of Documents
            if a sequence of texts was passed, with processed references and
            referents from the configured recognizer and resolver.
        """
        # A single text is parsed into a single document, so remember which
        # shape was asked for before normalizing the input
        single_text = isinstance(texts, str)

        # Create a new project for this parse operation
        project_name = uuid.uuid4().hex[:8]
        project = Project(project_name)

        try:
            # Create documents in the project
            document_ids = project.create_documents([texts] if single_text else texts)

            self._run_modules(project)

            # Get the documents back in input order, with results from our
            # specific recognizer and resolver
            documents = project.get_documents(ids=document_ids)

            # If save is True, inform the user about the project name
            if save:
                print(f"Results saved under project name: {project_name}")

            return documents[0] if single_text else documents

        finally:
            # Clean up the project unless the user wants to save it
            if not save:
                project.delete()
