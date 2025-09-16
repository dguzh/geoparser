from unittest.mock import MagicMock

import pytest
from sqlmodel import Session, SQLModel
from sqlmodel.pool import StaticPool

from geoparser.db.db import create_engine
from geoparser.db.models import Document, DocumentCreate, Project, ProjectCreate
from geoparser.db.models import Recognizer as RecognizerModel
from geoparser.db.models import RecognizerCreate, Reference, ReferenceCreate
from geoparser.modules.resolvers import Resolver


@pytest.fixture(scope="function")
def test_db():
    """Create a test database session."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def test_project(test_db: Session):
    """Create a test project."""
    project_create = ProjectCreate(name="test-project")
    project = Project(name=project_create.name)
    test_db.add(project)
    test_db.commit()
    test_db.refresh(project)
    return project


@pytest.fixture
def test_document(test_db, test_project):
    """Create a test document in the test project."""
    document_create = DocumentCreate(
        text="This is a test document about London and Paris.",
        project_id=test_project.id,
    )
    document = Document.model_validate(document_create)
    test_db.add(document)
    test_db.commit()
    test_db.refresh(document)
    return document


@pytest.fixture
def test_documents(test_db, test_project):
    """Create multiple test documents in the test project."""
    documents = []
    texts = [
        "This is a test document about London and Paris.",
        "Another document mentioning New York and Tokyo.",
    ]

    for text in texts:
        document_create = DocumentCreate(text=text, project_id=test_project.id)
        document = Document.model_validate(document_create)
        test_db.add(document)
        test_db.commit()
        test_db.refresh(document)
        documents.append(document)

    return documents


@pytest.fixture
def test_recognizer(test_db):
    """Create a test recognizer."""
    recognizer_create = RecognizerCreate(
        name="test-recognizer", config={"model": "test-model"}
    )
    recognizer = RecognizerModel.model_validate(recognizer_create)
    test_db.add(recognizer)
    test_db.commit()
    test_db.refresh(recognizer)
    return recognizer


@pytest.fixture
def test_reference(test_db, test_document, test_recognizer):
    """Create a test reference in the test document."""
    reference_create = ReferenceCreate(
        start=29, end=35, document_id=test_document.id, recognizer_id=test_recognizer.id
    )
    reference = Reference.model_validate(reference_create)
    test_db.add(reference)
    test_db.commit()
    test_db.refresh(reference)
    return reference


@pytest.fixture
def test_references(test_db, test_documents, test_recognizer):
    """Create multiple test references in the test documents."""
    references = []
    reference_data = [
        (29, 35),  # "London" in first document
        (41, 46),  # "Paris" in first document
        (32, 40),  # "New York" in second document
    ]

    for i, (start, end) in enumerate(reference_data):
        doc = test_documents[i % len(test_documents)]
        reference_create = ReferenceCreate(
            start=start, end=end, document_id=doc.id, recognizer_id=test_recognizer.id
        )
        reference = Reference.model_validate(reference_create)
        test_db.add(reference)
        test_db.commit()
        test_db.refresh(reference)
        references.append(reference)

    return references


@pytest.fixture
def mock_resolver():
    """Create a mock resolver for testing."""
    resolver = MagicMock(spec=Resolver)
    resolver.name = "mock_resolver"
    resolver.config = {"param": "value"}
    resolver.predict_referents.return_value = [("test_gazetteer", "loc1")]
    return resolver
