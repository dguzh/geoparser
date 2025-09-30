from unittest.mock import MagicMock

import pytest
from sqlmodel import Session, SQLModel
from sqlmodel.pool import StaticPool

from geoparser.db.engine import create_engine
from geoparser.db.models import Document, DocumentCreate, Project, ProjectCreate
from geoparser.modules.recognizers import Recognizer


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
def mock_recognizer():
    """Create a mock recognizer for testing."""
    recognizer = MagicMock(spec=Recognizer)
    recognizer.name = "mock_recognizer"
    recognizer.config = {"param": "value"}
    recognizer.predict_references.return_value = [[(29, 35), (41, 46)]]
    return recognizer
