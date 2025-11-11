"""
Unit tests for geoparser/db/crud/context.py

Tests the ContextRepository class with custom query methods.
"""

import pytest
from sqlmodel import Session

from geoparser.db.crud import ContextRepository


@pytest.mark.unit
class TestContextRepositoryGetByProject:
    """Test the get_by_project method of ContextRepository."""

    def test_returns_contexts_for_project(
        self, test_session: Session, project_factory, context_factory
    ):
        """Test that get_by_project returns all contexts for a project."""
        # Arrange
        project = project_factory()
        context1 = context_factory(tag="tag1", project_id=project.id)
        context2 = context_factory(tag="tag2", project_id=project.id)

        # Act
        contexts = ContextRepository.get_by_project(test_session, project.id)

        # Assert
        assert len(contexts) == 2
        context_ids = [c.id for c in contexts]
        assert context1.id in context_ids
        assert context2.id in context_ids

    def test_returns_empty_list_for_project_without_contexts(
        self, test_session: Session, project_factory
    ):
        """Test that get_by_project returns empty list for project without contexts."""
        # Arrange
        project = project_factory()

        # Act
        contexts = ContextRepository.get_by_project(test_session, project.id)

        # Assert
        assert contexts == []

    def test_filters_by_project(
        self, test_session: Session, project_factory, context_factory
    ):
        """Test that get_by_project only returns contexts from specified project."""
        # Arrange
        project1 = project_factory(name="Project 1")
        project2 = project_factory(name="Project 2")

        # Contexts in project1
        context1_proj1 = context_factory(tag="tag1", project_id=project1.id)

        # Contexts in project2
        context1_proj2 = context_factory(tag="tag1", project_id=project2.id)

        # Act - Get contexts from project1
        contexts = ContextRepository.get_by_project(test_session, project1.id)

        # Assert - Should only contain context from project1
        assert len(contexts) == 1
        assert contexts[0].id == context1_proj1.id
        assert contexts[0].tag == "tag1"


@pytest.mark.unit
class TestContextRepositoryGetByProjectAndTag:
    """Test the get_by_project_and_tag method of ContextRepository."""

    def test_returns_context_for_matching_project_and_tag(
        self, test_session: Session, project_factory, context_factory
    ):
        """Test that get_by_project_and_tag returns context when project and tag match."""
        # Arrange
        project = project_factory()
        context = context_factory(tag="my-tag", project_id=project.id)

        # Act
        found_context = ContextRepository.get_by_project_and_tag(
            test_session, project.id, "my-tag"
        )

        # Assert
        assert found_context is not None
        assert found_context.id == context.id
        assert found_context.tag == "my-tag"
        assert found_context.project_id == project.id

    def test_returns_none_for_non_matching_tag(
        self, test_session: Session, project_factory, context_factory
    ):
        """Test that get_by_project_and_tag returns None when tag doesn't match."""
        # Arrange
        project = project_factory()
        context = context_factory(tag="my-tag", project_id=project.id)

        # Act
        found_context = ContextRepository.get_by_project_and_tag(
            test_session, project.id, "other-tag"
        )

        # Assert
        assert found_context is None

    def test_returns_none_for_non_matching_project(
        self, test_session: Session, project_factory, context_factory
    ):
        """Test that get_by_project_and_tag returns None when project doesn't match."""
        # Arrange
        project1 = project_factory()
        project2 = project_factory()
        context = context_factory(tag="my-tag", project_id=project1.id)

        # Act
        found_context = ContextRepository.get_by_project_and_tag(
            test_session, project2.id, "my-tag"
        )

        # Assert
        assert found_context is None

    def test_returns_correct_context_when_multiple_exist(
        self, test_session: Session, project_factory, context_factory
    ):
        """Test that get_by_project_and_tag returns correct context when multiple exist."""
        # Arrange
        project = project_factory()
        context1 = context_factory(tag="tag-a", project_id=project.id)
        context2 = context_factory(tag="tag-b", project_id=project.id)
        context3 = context_factory(tag="tag-c", project_id=project.id)

        # Act
        found_context = ContextRepository.get_by_project_and_tag(
            test_session, project.id, "tag-b"
        )

        # Assert
        assert found_context is not None
        assert found_context.id == context2.id
        assert found_context.tag == "tag-b"

    def test_handles_context_with_none_ids(
        self, test_session: Session, project_factory, context_factory
    ):
        """Test that get_by_project_and_tag works with contexts that have None IDs."""
        # Arrange
        project = project_factory()
        context = context_factory(
            tag="none-tag", project_id=project.id, recognizer_id=None, resolver_id=None
        )

        # Act
        found_context = ContextRepository.get_by_project_and_tag(
            test_session, project.id, "none-tag"
        )

        # Assert
        assert found_context is not None
        assert found_context.recognizer_id is None
        assert found_context.resolver_id is None
