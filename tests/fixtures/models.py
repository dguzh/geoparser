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
    ContextRepository,
    DocumentRepository,
    FeatureRepository,
    GazetteerRepository,
    NameRepository,
    ProjectRepository,
    RecognizerRepository,
    ReferenceRepository,
    ResolverRepository,
    SourceRepository,
)
from geoparser.db.models import (
    ContextCreate,
    DocumentCreate,
    FeatureCreate,
    GazetteerCreate,
    NameCreate,
    ProjectCreate,
    RecognizerCreate,
    ReferenceCreate,
    ResolverCreate,
    SourceCreate,
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
def context_factory(
    test_session: Session,
    project_factory: Callable,
) -> Callable:
    """
    Factory for creating test context records.

    Args:
        test_session: Database session fixture
        project_factory: Project factory fixture

    Returns:
        Function that creates contexts with optional custom attributes
    """

    def _create_context(
        tag: Optional[str] = None,
        project_id: Optional[uuid.UUID] = None,
        recognizer_id: Optional[str] = None,
        resolver_id: Optional[str] = None,
        **kwargs,
    ):
        """
        Create a context with the given attributes.

        Args:
            tag: Context tag (auto-generated if not provided)
            project_id: ID of parent project (creates new project if not provided)
            recognizer_id: ID of recognizer (optional)
            resolver_id: ID of resolver (optional)
            **kwargs: Additional attributes to set on the context

        Returns:
            Created Context instance
        """
        if tag is None:
            tag = f"test_tag_{uuid.uuid4().hex[:8]}"

        if project_id is None:
            project = project_factory()
            project_id = project.id

        context_create = ContextCreate(
            tag=tag,
            project_id=project_id,
            recognizer_id=recognizer_id,
            resolver_id=resolver_id,
            **kwargs,
        )
        return ContextRepository.create(test_session, context_create)

    return _create_context


@pytest.fixture
def gazetteer_factory(test_session: Session) -> Callable:
    """
    Factory for creating test gazetteers.

    Args:
        test_session: Database session fixture

    Returns:
        Function that creates gazetteers with optional custom attributes
    """

    def _create_gazetteer(name: Optional[str] = None, **kwargs):
        """
        Create a gazetteer with the given attributes.

        Args:
            name: Gazetteer name (auto-generated if not provided)
            **kwargs: Additional attributes to set on the gazetteer

        Returns:
            Created Gazetteer instance
        """
        if name is None:
            name = f"test_gazetteer_{uuid.uuid4().hex[:8]}"

        gazetteer_create = GazetteerCreate(name=name, **kwargs)
        return GazetteerRepository.create(test_session, gazetteer_create)

    return _create_gazetteer


@pytest.fixture
def source_factory(test_session: Session, gazetteer_factory: Callable) -> Callable:
    """
    Factory for creating test sources.

    Args:
        test_session: Database session fixture
        gazetteer_factory: Gazetteer factory fixture

    Returns:
        Function that creates sources with optional custom attributes
    """

    def _create_source(
        name: Optional[str] = None,
        location_id_name: Optional[str] = None,
        gazetteer_id: Optional[uuid.UUID] = None,
        **kwargs,
    ):
        """
        Create a source with the given attributes.

        Args:
            name: Source name (auto-generated if not provided)
            location_id_name: Name of the location ID field (default: "id")
            gazetteer_id: ID of parent gazetteer (creates new gazetteer if not provided)
            **kwargs: Additional attributes to set on the source

        Returns:
            Created Source instance
        """
        if name is None:
            name = f"test_source_{uuid.uuid4().hex[:8]}"

        if location_id_name is None:
            location_id_name = "id"

        if gazetteer_id is None:
            gazetteer = gazetteer_factory()
            gazetteer_id = gazetteer.id

        source_create = SourceCreate(
            name=name,
            location_id_name=location_id_name,
            gazetteer_id=gazetteer_id,
            **kwargs,
        )
        return SourceRepository.create(test_session, source_create)

    return _create_source


@pytest.fixture
def feature_factory(test_session: Session, source_factory: Callable) -> Callable:
    """
    Factory for creating test features.

    Args:
        test_session: Database session fixture
        source_factory: Source factory fixture

    Returns:
        Function that creates features with optional custom attributes
    """

    def _create_feature(
        location_id_value: Optional[str] = None,
        source_id: Optional[int] = None,
        **kwargs,
    ):
        """
        Create a feature with the given attributes.

        Args:
            location_id_value: Location ID value (auto-generated if not provided)
            source_id: ID of parent source (creates new source if not provided)
            **kwargs: Additional attributes to set on the feature

        Returns:
            Created Feature instance
        """
        if location_id_value is None:
            location_id_value = str(uuid.uuid4().int)[:8]

        if source_id is None:
            source = source_factory()
            source_id = source.id

        feature_create = FeatureCreate(
            location_id_value=location_id_value, source_id=source_id, **kwargs
        )
        return FeatureRepository.create(test_session, feature_create)

    return _create_feature


@pytest.fixture
def name_factory(test_session: Session, feature_factory: Callable) -> Callable:
    """
    Factory for creating test names.

    Args:
        test_session: Database session fixture
        feature_factory: Feature factory fixture

    Returns:
        Function that creates names with optional custom attributes
    """

    def _create_name(
        text: Optional[str] = None, feature_id: Optional[int] = None, **kwargs
    ):
        """
        Create a name with the given attributes.

        Args:
            text: Name text (auto-generated if not provided)
            feature_id: ID of parent feature (creates new feature if not provided)
            **kwargs: Additional attributes to set on the name

        Returns:
            Created Name instance
        """
        if text is None:
            text = f"test_name_{uuid.uuid4().hex[:8]}"

        if feature_id is None:
            feature = feature_factory()
            feature_id = feature.id

        name_create = NameCreate(text=text, feature_id=feature_id, **kwargs)
        return NameRepository.create(test_session, name_create)

    return _create_name
