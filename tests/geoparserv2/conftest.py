from unittest.mock import patch

import pytest
from sqlmodel import Session, SQLModel
from sqlmodel.pool import StaticPool

from geoparser.db.db import create_engine
from geoparser.db.models import Project, ProjectCreate
from geoparser.geoparserv2.project_manager import ProjectManager


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
    with patch("geoparser.geoparserv2.project_manager.get_db") as mock:
        mock.return_value = iter([test_db])
        yield mock


@pytest.fixture
def project_manager_with_existing_project(mock_get_db, test_project):
    """Create a ProjectManager instance with an existing project."""
    return ProjectManager(project_name=test_project.name)


@pytest.fixture
def project_manager_with_new_project(mock_get_db):
    """Create a ProjectManager instance with a new project."""
    return ProjectManager(project_name="new-test-project")
