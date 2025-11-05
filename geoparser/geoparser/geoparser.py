import uuid
import warnings
from typing import List, Optional, Union

from geoparser.db.models import Document
from geoparser.modules.recognizers import Recognizer
from geoparser.modules.resolvers import Resolver
from geoparser.project import Project

# Sentinel value to distinguish "not provided" from "explicitly None"
_UNSET = object()


class Geoparser:
    """
    User-facing interface for the geoparser functionality.

    Provides a simple parse method for processing texts with configured recognizer and resolver.
    The Geoparser creates a new project for each parse operation, making it stateless by default.
    """

    def __init__(
        self,
        recognizer: Optional[Recognizer] = _UNSET,
        resolver: Optional[Resolver] = _UNSET,
        spacy_model: Optional[str] = None,
        transformer_model: Optional[str] = None,
    ):
        """
        Initialize a Geoparser instance.

        Args:
            recognizer: The recognizer module to use for identifying references.
                       If not provided, a default SpacyRecognizer will be created.
                       Can be explicitly set to None to skip recognition step.
            resolver: The resolver module to use for resolving references to referents.
                     If not provided, a default SentenceTransformerResolver will be created.
                     Can be explicitly set to None to skip resolution step.
            spacy_model: (Deprecated) Name of spaCy model to use.
                        Use SpacyRecognizer(model_name='...') instead.
            transformer_model: (Deprecated) Name of transformer model to use.
                              Use SentenceTransformerResolver(model_name='...') instead.
        """
        # Handle legacy parameters with deprecation warning
        self._warn_deprecated_parameters(spacy_model, transformer_model)

        # Set up recognizer
        if recognizer is _UNSET:
            # No recognizer provided, create default
            from geoparser.modules import SpacyRecognizer

            if spacy_model is not None:
                self.recognizer = SpacyRecognizer(model_name=spacy_model)
            else:
                self.recognizer = SpacyRecognizer()
        else:
            # Recognizer explicitly provided (could be None to skip)
            self.recognizer = recognizer

        # Set up resolver
        if resolver is _UNSET:
            # No resolver provided, create default
            from geoparser.modules import SentenceTransformerResolver

            if transformer_model is not None:
                self.resolver = SentenceTransformerResolver(
                    model_name=transformer_model
                )
            else:
                self.resolver = SentenceTransformerResolver()
        else:
            # Resolver explicitly provided (could be None to skip)
            self.resolver = resolver

    @staticmethod
    def _warn_deprecated_parameters(
        spacy_model: Optional[str], transformer_model: Optional[str]
    ) -> None:
        """
        Show deprecation warning for legacy parameters.

        Args:
            spacy_model: Legacy spacy_model parameter value
            transformer_model: Legacy transformer_model parameter value
        """
        # Collect all legacy parameters used
        legacy_params = []
        if spacy_model is not None:
            legacy_params.append(
                ("spacy_model", spacy_model, "SpacyRecognizer", "recognizer")
            )
        if transformer_model is not None:
            legacy_params.append(
                (
                    "transformer_model",
                    transformer_model,
                    "SentenceTransformerResolver",
                    "resolver",
                )
            )

        # Show a single consolidated warning if any legacy parameters are used
        if not legacy_params:
            return

        # List the deprecated parameters
        param_names = ", ".join([f"'{param}'" for param, _, _, _ in legacy_params])
        warning_parts = [
            f"Deprecated parameter{'s' if len(legacy_params) > 1 else ''} detected: {param_names}. "
            "The Geoparser now uses a module-based architecture "
            "where you create and configure recognizer and resolver modules explicitly.\n"
        ]

        # Build the old usage example
        old_params = ",\n        ".join(
            [f"{param}='{value}'" for param, value, _, _ in legacy_params]
        )

        warning_parts.append("Instead of:")
        warning_parts.append(f"    Geoparser(\n        {old_params}\n    )\n")

        # Build the new usage example
        warning_parts.append("Please use:")
        imports = [f"{module_class}" for _, _, module_class, _ in legacy_params]
        warning_parts.append(
            f"    from geoparser.modules import {', '.join(imports)}\n"
        )

        new_params = ",\n        ".join(
            [
                f"{arg_name}={module_class}(model_name='{value}')"
                for _, value, module_class, arg_name in legacy_params
            ]
        )
        warning_parts.append(f"    Geoparser(\n        {new_params}\n    )\n\n")

        # Use simplefilter to control how the warning is displayed
        with warnings.catch_warnings():
            warnings.simplefilter("always", DeprecationWarning)
            warnings.warn("\n".join(warning_parts), DeprecationWarning, stacklevel=3)

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
            # Create documents in the project
            project.create_documents(texts)

            # Run the recognizer on all documents (if provided)
            if self.recognizer is not None:
                project.run_recognizer(self.recognizer)

            # Run the resolver on all documents (if provided)
            if self.resolver is not None:
                project.run_resolver(self.resolver)

            # Get all documents with results from our specific recognizer and resolver
            documents = project.get_documents()

            # If save is True, inform the user about the project name
            if save:
                print(f"Results saved under project name: {project_name}")

            return documents

        finally:
            # Clean up the project unless the user wants to save it
            if not save:
                project.delete()
