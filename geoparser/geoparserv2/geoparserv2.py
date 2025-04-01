from typing import List, Optional, Union

from geoparser.db.models import Document
from geoparser.geoparserv2.module_interfaces import BaseModule
from geoparser.geoparserv2.module_runner import ModuleRunner
from geoparser.geoparserv2.project_manager import ProjectManager


class GeoparserV2:
    """
    User-facing wrapper for the geoparser functionality.

    Provides a simple interface for geoparsing operations with optional
    project persistence and configurable processing modules.
    """

    def __init__(
        self,
        project_name: Optional[str] = None,
        modules: Optional[List[BaseModule]] = None,
    ):
        """
        Initialize a GeoparserV2 instance.

        Args:
            project_name: Optional name for persistent project storage.
                          If None, creates a temporary project.
            modules: List of processing modules for text processing.
        """
        self.project_manager = ProjectManager(project_name=project_name)
        self.modules = modules or []
        self.module_runner = ModuleRunner()

    def parse(self, texts: Union[str, List[str]]) -> List[Document]:
        """
        Parse one or more texts with the configured modules.

        This method adds documents to the project, processes them with
        all configured modules, and returns the processed documents.

        Args:
            texts: Either a single document text or a list of texts

        Returns:
            List of Document objects with processed toponyms and locations
        """
        # Add documents to the project and get their IDs
        document_ids = self.project_manager.add_documents(texts)

        # Run each module on the project
        for module in self.modules:
            self.module_runner.run_module(module, self.project_manager.project_id)

        # Retrieve the processed documents using the project
        return self.project_manager.get_documents(document_ids)
