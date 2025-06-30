import uuid

from sqlmodel import Session

from geoparser.db.crud import ProjectRepository
from geoparser.db.models import Project, ProjectCreate, ProjectUpdate


def test_create(test_db: Session):
    """Test creating a project."""
    project_create = ProjectCreate(name="test-create-project")
    project = Project(name=project_create.name)

    created_project = ProjectRepository.create(test_db, project)

    assert created_project.id is not None
    assert created_project.name == "test-create-project"

    # Verify it was saved to the database
    db_project = test_db.get(Project, created_project.id)
    assert db_project is not None
    assert db_project.name == "test-create-project"


def test_get(test_db: Session, test_project: Project):
    """Test getting a project by ID."""
    # Test with valid ID
    project = ProjectRepository.get(test_db, test_project.id)
    assert project is not None
    assert project.id == test_project.id
    assert project.name == test_project.name

    # Test with invalid ID
    invalid_id = uuid.uuid4()
    project = ProjectRepository.get(test_db, invalid_id)
    assert project is None


def test_get_by_name(test_db: Session, test_project: Project):
    """Test getting a project by name."""
    # Test with valid name
    project = ProjectRepository.get_by_name(test_db, test_project.name)
    assert project is not None
    assert project.id == test_project.id
    assert project.name == test_project.name

    # Test with invalid name
    project = ProjectRepository.get_by_name(test_db, "non-existent-project")
    assert project is None


def test_get_all(test_db: Session, test_project: Project):
    """Test getting all projects."""
    # Create another project
    project_create = ProjectCreate(name="another-test-project")
    project = Project(name=project_create.name)
    test_db.add(project)
    test_db.commit()

    # Get all projects
    projects = ProjectRepository.get_all(test_db)
    assert len(projects) == 2
    assert any(s.name == "test-project" for s in projects)
    assert any(s.name == "another-test-project" for s in projects)


def test_update(test_db: Session, test_project: Project):
    """Test updating a project."""
    # Update the project
    project_update = ProjectUpdate(id=test_project.id, name="updated-project")
    updated_project = ProjectRepository.update(
        test_db, db_obj=test_project, obj_in=project_update
    )

    assert updated_project.id == test_project.id
    assert updated_project.name == "updated-project"

    # Verify it was updated in the database
    db_project = test_db.get(Project, test_project.id)
    assert db_project is not None
    assert db_project.name == "updated-project"


def test_delete(test_db: Session, test_project: Project):
    """Test deleting a project."""
    # Delete the project
    deleted_project = ProjectRepository.delete(test_db, id=test_project.id)

    assert deleted_project is not None
    assert deleted_project.id == test_project.id

    # Verify it was deleted from the database
    db_project = test_db.get(Project, test_project.id)
    assert db_project is None
