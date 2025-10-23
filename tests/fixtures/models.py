"""
Model factories for creating test data.

Provides fixture factories for easily creating test instances of database models.
These factories help reduce boilerplate in tests and ensure consistent test data.
"""

import uuid
from typing import Callable, Optional

import pytest
from sqlmodel import Session

from geoparser.db.crud import (
    DocumentRepository,
    ProjectRepository,
    RecognizerRepository,
    ReferenceRepository,
    ResolverRepository,
)
from geoparser.db.models import (
    DocumentCreate,
    ProjectCreate,
    RecognizerCreate,
    ReferenceCreate,
    ResolverCreate,
)


@pytest.fixture
def project_factory(test_session: Session) -> Callable:
    """
    Factory for creating test projects.

    Args:
        test_session: Database session fixture

    Returns:
        Function that creates projects with optional custom attributes
    """

    def _create_project(name: Optional[str] = None, **kwargs):
        """
        Create a project with the given attributes.

        Args:
            name: Project name (auto-generated if not provided)
            **kwargs: Additional attributes to set on the project

        Returns:
            Created Project instance
        """
        if name is None:
            name = f"test_project_{uuid.uuid4().hex[:8]}"

        project_create = ProjectCreate(name=name, **kwargs)
        return ProjectRepository.create(test_session, project_create)

    return _create_project


@pytest.fixture
def document_factory(test_session: Session, project_factory: Callable) -> Callable:
    """
    Factory for creating test documents.

    Args:
        test_session: Database session fixture
        project_factory: Project factory fixture

    Returns:
        Function that creates documents with optional custom attributes
    """

    def _create_document(
        text: Optional[str] = None, project_id: Optional[uuid.UUID] = None, **kwargs
    ):
        """
        Create a document with the given attributes.

        Args:
            text: Document text (default text if not provided)
            project_id: ID of parent project (creates new project if not provided)
            **kwargs: Additional attributes to set on the document

        Returns:
            Created Document instance
        """
        if text is None:
            text = "This is a test document."

        if project_id is None:
            project = project_factory()
            project_id = project.id

        document_create = DocumentCreate(text=text, project_id=project_id, **kwargs)
        return DocumentRepository.create(test_session, document_create)

    return _create_document


@pytest.fixture
def recognizer_factory(test_session: Session) -> Callable:
    """
    Factory for creating test recognizer records.

    Args:
        test_session: Database session fixture

    Returns:
        Function that creates recognizers with optional custom attributes
    """

    def _create_recognizer(
        id: Optional[str] = None,
        name: Optional[str] = None,
        config: Optional[dict] = None,
        **kwargs,
    ):
        """
        Create a recognizer with the given attributes.

        Args:
            id: Recognizer ID (auto-generated if not provided)
            name: Recognizer name (default name if not provided)
            config: Recognizer configuration (empty dict if not provided)
            **kwargs: Additional attributes to set on the recognizer

        Returns:
            Created Recognizer instance
        """
        if id is None:
            id = f"test_rec_{uuid.uuid4().hex[:8]}"

        if name is None:
            name = "TestRecognizer"

        if config is None:
            config = {}

        recognizer_create = RecognizerCreate(id=id, name=name, config=config, **kwargs)
        return RecognizerRepository.create(test_session, recognizer_create)

    return _create_recognizer


@pytest.fixture
def resolver_factory(test_session: Session) -> Callable:
    """
    Factory for creating test resolver records.

    Args:
        test_session: Database session fixture

    Returns:
        Function that creates resolvers with optional custom attributes
    """

    def _create_resolver(
        id: Optional[str] = None,
        name: Optional[str] = None,
        config: Optional[dict] = None,
        **kwargs,
    ):
        """
        Create a resolver with the given attributes.

        Args:
            id: Resolver ID (auto-generated if not provided)
            name: Resolver name (default name if not provided)
            config: Resolver configuration (empty dict if not provided)
            **kwargs: Additional attributes to set on the resolver

        Returns:
            Created Resolver instance
        """
        if id is None:
            id = f"test_res_{uuid.uuid4().hex[:8]}"

        if name is None:
            name = "TestResolver"

        if config is None:
            config = {}

        resolver_create = ResolverCreate(id=id, name=name, config=config, **kwargs)
        return ResolverRepository.create(test_session, resolver_create)

    return _create_resolver


@pytest.fixture
def reference_factory(
    test_session: Session, document_factory: Callable, recognizer_factory: Callable
) -> Callable:
    """
    Factory for creating test references.

    Args:
        test_session: Database session fixture
        document_factory: Document factory fixture
        recognizer_factory: Recognizer factory fixture

    Returns:
        Function that creates references with optional custom attributes
    """

    def _create_reference(
        start: int = 0,
        end: int = 4,
        text: Optional[str] = None,
        document_id: Optional[uuid.UUID] = None,
        recognizer_id: Optional[str] = None,
        **kwargs,
    ):
        """
        Create a reference with the given attributes.

        Args:
            start: Start position in document (default: 0)
            end: End position in document (default: 4)
            text: Reference text (optional, extracted from document if not provided)
            document_id: ID of parent document (creates new document if not provided)
            recognizer_id: ID of recognizer (creates new recognizer if not provided)
            **kwargs: Additional attributes to set on the reference

        Returns:
            Created Reference instance
        """
        if document_id is None:
            document = document_factory()
            document_id = document.id

        if recognizer_id is None:
            recognizer = recognizer_factory()
            recognizer_id = recognizer.id

        reference_create = ReferenceCreate(
            start=start,
            end=end,
            text=text,
            document_id=document_id,
            recognizer_id=recognizer_id,
            **kwargs,
        )
        return ReferenceRepository.create(test_session, reference_create)

    return _create_reference
