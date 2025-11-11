"""
Unit tests for geoparser/db/crud/base.py

Tests the BaseRepository class with common CRUD operations.
"""

import uuid

import pytest
from sqlmodel import Session

from geoparser.db.crud import ProjectRepository
from geoparser.db.models import ProjectCreate, ProjectUpdate


@pytest.mark.unit
class TestBaseRepositoryCreate:
    """Test the create method of BaseRepository."""

    def test_creates_record_successfully(self, test_session: Session):
        """Test that create method creates a new record in the database."""
        # Arrange
        project_create = ProjectCreate(name="New Project")

        # Act
        project = ProjectRepository.create(test_session, project_create)

        # Assert
        assert project.id is not None
        assert project.name == "New Project"

    def test_persists_record_to_database(self, test_session: Session):
        """Test that created record is actually persisted to database."""
        # Arrange
        project_create = ProjectCreate(name="Persistent Project")

        # Act
        created_project = ProjectRepository.create(test_session, project_create)

        # Assert - Query the database to verify persistence
        retrieved_project = ProjectRepository.get(test_session, created_project.id)
        assert retrieved_project is not None
        assert retrieved_project.id == created_project.id
        assert retrieved_project.name == "Persistent Project"


@pytest.mark.unit
class TestBaseRepositoryGet:
    """Test the get method of BaseRepository."""

    def test_retrieves_existing_record(self, test_session: Session, project_factory):
        """Test that get method retrieves an existing record by ID."""
        # Arrange
        project = project_factory(name="Test Project")

        # Act
        retrieved = ProjectRepository.get(test_session, project.id)

        # Assert
        assert retrieved is not None
        assert retrieved.id == project.id
        assert retrieved.name == "Test Project"

    def test_returns_none_for_nonexistent_id(self, test_session: Session):
        """Test that get method returns None for non-existent ID."""
        # Arrange
        nonexistent_id = uuid.uuid4()

        # Act
        retrieved = ProjectRepository.get(test_session, nonexistent_id)

        # Assert
        assert retrieved is None

    def test_accepts_string_id(self, test_session: Session, recognizer_factory):
        """Test that get method accepts string IDs (for recognizers/resolvers)."""
        # Arrange
        recognizer = recognizer_factory(id="test_id", name="Test Recognizer")

        # Act
        from geoparser.db.crud import RecognizerRepository

        retrieved = RecognizerRepository.get(test_session, "test_id")

        # Assert
        assert retrieved is not None
        assert retrieved.id == "test_id"


@pytest.mark.unit
class TestBaseRepositoryGetAll:
    """Test the get_all method of BaseRepository."""

    def test_retrieves_all_records(self, test_session: Session, project_factory):
        """Test that get_all retrieves all records of the model."""
        # Arrange
        project1 = project_factory(name="Project 1")
        project2 = project_factory(name="Project 2")
        project3 = project_factory(name="Project 3")

        # Act
        all_projects = ProjectRepository.get_all(test_session)

        # Assert
        assert len(all_projects) == 3
        project_names = [p.name for p in all_projects]
        assert "Project 1" in project_names
        assert "Project 2" in project_names
        assert "Project 3" in project_names

    def test_returns_empty_list_when_no_records(self, test_session: Session):
        """Test that get_all returns empty list when no records exist."""
        # Arrange & Act
        all_projects = ProjectRepository.get_all(test_session)

        # Assert
        assert all_projects == []


@pytest.mark.unit
class TestBaseRepositoryUpdate:
    """Test the update method of BaseRepository."""

    def test_updates_record_successfully(self, test_session: Session, project_factory):
        """Test that update method modifies an existing record."""
        # Arrange
        project = project_factory(name="Original Name")
        project_update = ProjectUpdate(id=project.id, name="Updated Name")

        # Act
        updated_project = ProjectRepository.update(
            test_session, db_obj=project, obj_in=project_update
        )

        # Assert
        assert updated_project.id == project.id
        assert updated_project.name == "Updated Name"

    def test_persists_updates_to_database(self, test_session: Session, project_factory):
        """Test that updates are actually persisted to database."""
        # Arrange
        project = project_factory(name="Original")
        project_update = ProjectUpdate(id=project.id, name="Modified")

        # Act
        ProjectRepository.update(test_session, db_obj=project, obj_in=project_update)

        # Assert - Query to verify persistence
        retrieved = ProjectRepository.get(test_session, project.id)
        assert retrieved.name == "Modified"

    def test_only_updates_provided_fields(self, test_session: Session, project_factory):
        """Test that update only modifies fields provided in update model."""
        # Arrange
        project = project_factory(name="Original Name")
        # ProjectUpdate with only id (name is optional and not provided)
        project_update = ProjectUpdate(id=project.id)

        # Act
        updated_project = ProjectRepository.update(
            test_session, db_obj=project, obj_in=project_update
        )

        # Assert - Name should remain unchanged
        assert updated_project.name == "Original Name"


@pytest.mark.unit
class TestBaseRepositoryDelete:
    """Test the delete method of BaseRepository."""

    def test_deletes_record_successfully(self, test_session: Session, project_factory):
        """Test that delete method removes a record from database."""
        # Arrange
        project = project_factory(name="To Delete")
        project_id = project.id

        # Act
        deleted_project = ProjectRepository.delete(test_session, id=project_id)

        # Assert
        assert deleted_project is not None
        assert deleted_project.id == project_id

        # Verify deletion
        retrieved = ProjectRepository.get(test_session, project_id)
        assert retrieved is None

    def test_returns_none_when_deleting_nonexistent_record(self, test_session: Session):
        """Test that delete returns None when trying to delete non-existent record."""
        # Arrange
        nonexistent_id = uuid.uuid4()

        # Act
        deleted = ProjectRepository.delete(test_session, id=nonexistent_id)

        # Assert
        assert deleted is None

    def test_cascades_to_related_records(
        self, test_session: Session, project_factory, document_factory
    ):
        """Test that delete cascades to related records when configured."""
        # Arrange
        project = project_factory(name="Parent")
        doc1 = document_factory(text="Doc 1", project_id=project.id)
        doc2 = document_factory(text="Doc 2", project_id=project.id)

        # Store IDs before deletion (objects will be detached after)
        doc1_id = doc1.id
        doc2_id = doc2.id

        # Act
        ProjectRepository.delete(test_session, id=project.id)

        # Assert - Documents should be deleted due to cascade
        from geoparser.db.crud import DocumentRepository

        remaining_doc1 = DocumentRepository.get(test_session, doc1_id)
        remaining_doc2 = DocumentRepository.get(test_session, doc2_id)
        assert remaining_doc1 is None
        assert remaining_doc2 is None
