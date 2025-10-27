"""
Unit tests for geoparser/db/models/project.py

Tests the Project model, including creation, validation, and relationships.
"""

import uuid

import pytest
from sqlmodel import Session

from geoparser.db.models import Project, ProjectCreate, ProjectUpdate


@pytest.mark.unit
class TestProjectModel:
    """Test the Project model."""

    def test_creates_project_with_valid_data(self, test_session: Session):
        """Test that a Project can be created with valid data."""
        # Arrange
        project = Project(name="Test Project")

        # Act
        test_session.add(project)
        test_session.commit()
        test_session.refresh(project)

        # Assert
        assert project.id is not None
        assert isinstance(project.id, uuid.UUID)
        assert project.name == "Test Project"

    def test_generates_uuid_automatically(self, test_session: Session):
        """Test that Project automatically generates a UUID for id."""
        # Arrange
        project = Project(name="Test")

        # Act
        test_session.add(project)
        test_session.commit()

        # Assert
        assert project.id is not None
        assert isinstance(project.id, uuid.UUID)

    def test_name_is_indexed(self, test_session: Session):
        """Test that the name field is indexed for efficient queries."""
        # Arrange
        project = Project(name="Indexed Project")
        test_session.add(project)
        test_session.commit()

        # Act - Query by name should work efficiently
        from sqlmodel import select

        statement = select(Project).where(Project.name == "Indexed Project")
        result = test_session.exec(statement).first()

        # Assert
        assert result is not None
        assert result.name == "Indexed Project"

    def test_has_documents_relationship(self, test_session: Session):
        """Test that Project has a relationship to documents."""
        # Arrange
        project = Project(name="Test")
        test_session.add(project)
        test_session.commit()

        # Assert
        assert hasattr(project, "documents")
        assert isinstance(project.documents, list)
        assert len(project.documents) == 0

    def test_cascade_deletes_documents(self, test_session: Session, document_factory):
        """Test that deleting a project cascades to delete its documents."""
        # Arrange
        project = Project(name="Test")
        test_session.add(project)
        test_session.commit()
        test_session.refresh(project)

        # Add documents using the factory
        doc1 = document_factory(text="Doc 1", project_id=project.id)
        doc2 = document_factory(text="Doc 2", project_id=project.id)

        # Act - Delete the project
        test_session.delete(project)
        test_session.commit()

        # Assert - Documents should be deleted
        from sqlmodel import select

        from geoparser.db.models import Document

        statement = select(Document).where(Document.project_id == project.id)
        remaining_docs = test_session.exec(statement).all()
        assert len(remaining_docs) == 0


@pytest.mark.unit
class TestProjectCreate:
    """Test the ProjectCreate model."""

    def test_creates_with_name(self):
        """Test that ProjectCreate can be created with just a name."""
        # Arrange & Act
        project_create = ProjectCreate(name="New Project")

        # Assert
        assert project_create.name == "New Project"

    def test_validates_required_fields(self):
        """Test that ProjectCreate validates required fields."""
        # Arrange & Act & Assert
        with pytest.raises(Exception):  # Pydantic will raise ValidationError
            ProjectCreate()  # Missing required 'name' field


@pytest.mark.unit
class TestProjectUpdate:
    """Test the ProjectUpdate model."""

    def test_creates_update_with_id_and_name(self):
        """Test that ProjectUpdate can be created with id and name."""
        # Arrange
        project_id = uuid.uuid4()

        # Act
        project_update = ProjectUpdate(id=project_id, name="Updated Name")

        # Assert
        assert project_update.id == project_id
        assert project_update.name == "Updated Name"

    def test_allows_optional_name(self):
        """Test that ProjectUpdate allows name to be optional."""
        # Arrange
        project_id = uuid.uuid4()

        # Act
        project_update = ProjectUpdate(id=project_id)

        # Assert
        assert project_update.id == project_id
        assert project_update.name is None
