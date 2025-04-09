from unittest.mock import MagicMock, patch

import pytest
from sqlmodel import Session, SQLModel
from sqlmodel.pool import StaticPool

from geoparser.db.db import create_engine
from geoparser.db.models import (
    Document,
    DocumentCreate,
    Project,
    ProjectCreate,
    Toponym,
    ToponymCreate,
)
from geoparser.geoparserv2.geoparserv2 import GeoparserV2
from geoparser.geoparserv2.orchestrator import Orchestrator
from geoparser.modules.interfaces import (
    AbstractRecognitionModule,
    AbstractResolutionModule,
)


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
def mock_get_db(test_db):
    """Mock the get_db function to return our test database session."""
    with patch("geoparser.geoparserv2.geoparserv2.get_db") as mock:
        mock.return_value = iter([test_db])
        yield mock


@pytest.fixture
def geoparser_with_existing_project(mock_get_db, test_project):
    """Create a GeoparserV2 instance with an existing project."""
    return GeoparserV2(project_name=test_project.name)


@pytest.fixture
def geoparser_with_new_project(mock_get_db):
    """Create a GeoparserV2 instance with a new project."""
    return GeoparserV2(project_name="new-test-project")


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
def test_toponym(test_db, test_document):
    """Create a test toponym in the test document."""
    toponym_create = ToponymCreate(start=27, end=33, document_id=test_document.id)
    toponym = Toponym.model_validate(toponym_create)
    test_db.add(toponym)
    test_db.commit()
    test_db.refresh(toponym)
    return toponym


@pytest.fixture
def mock_recognition_module():
    """Create a mock recognition module for testing."""
    module = MagicMock(spec=AbstractRecognitionModule)
    module.name = "mock_recognition"
    module.config = {"param": "value"}
    module.predict_toponyms.return_value = [[(27, 33), (39, 44)]]
    return module


@pytest.fixture
def mock_resolution_module():
    """Create a mock resolution module for testing."""
    module = MagicMock(spec=AbstractResolutionModule)
    module.name = "mock_resolution"
    module.config = {"param": "value"}
    module.predict_locations.return_value = [[("loc1", 0.8), ("loc2", 0.6)]]
    return module


@pytest.fixture
def orchestrator():
    """Create an Orchestrator instance for testing."""
    return Orchestrator()
