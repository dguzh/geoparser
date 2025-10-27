"""
Unit tests for geoparser/db/crud/project.py

Tests the ProjectRepository class with custom query methods.
"""

import pytest
from sqlmodel import Session

from geoparser.db.crud import ProjectRepository


@pytest.mark.unit
class TestProjectRepositoryGetByName:
    """Test the get_by_name method of ProjectRepository."""

    def test_returns_project_for_matching_name(
        self, test_session: Session, project_factory
    ):
        """Test that get_by_name returns project when name matches."""
        # Arrange
        project = project_factory(name="MyProject")

        # Act
        found_project = ProjectRepository.get_by_name(test_session, "MyProject")

        # Assert
        assert found_project is not None
        assert found_project.id == project.id
        assert found_project.name == "MyProject"

    def test_returns_none_for_non_matching_name(
        self, test_session: Session, project_factory
    ):
        """Test that get_by_name returns None when name doesn't match."""
        # Arrange
        project = project_factory(name="MyProject")

        # Act
        found_project = ProjectRepository.get_by_name(test_session, "OtherProject")

        # Assert
        assert found_project is None

    def test_returns_first_project_when_multiple_exist(
        self, test_session: Session, project_factory
    ):
        """Test that get_by_name returns first project when multiple exist (edge case)."""
        # Arrange
        project1 = project_factory(name="Project A")
        project2 = project_factory(name="Project B")

        # Act
        found_project = ProjectRepository.get_by_name(test_session, "Project A")

        # Assert
        assert found_project is not None
        assert found_project.id == project1.id
