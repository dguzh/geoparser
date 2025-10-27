"""
Unit tests for geoparser/db/crud/document.py

Tests the DocumentRepository class with custom query methods.
"""

import pytest
from sqlmodel import Session

from geoparser.db.crud import DocumentRepository


@pytest.mark.unit
class TestDocumentRepositoryGetByProject:
    """Test the get_by_project method of DocumentRepository."""

    def test_returns_documents_for_project(
        self,
        test_session: Session,
        project_factory,
        document_factory,
    ):
        """Test that get_by_project returns all documents for a project."""
        # Arrange
        project = project_factory()
        doc1 = document_factory(text="Document 1", project_id=project.id)
        doc2 = document_factory(text="Document 2", project_id=project.id)

        # Act
        documents = DocumentRepository.get_by_project(test_session, project.id)

        # Assert
        assert len(documents) == 2
        document_ids = [d.id for d in documents]
        assert doc1.id in document_ids
        assert doc2.id in document_ids

    def test_returns_empty_list_for_project_without_documents(
        self, test_session: Session, project_factory
    ):
        """Test that get_by_project returns empty list for project without documents."""
        # Arrange
        project = project_factory()

        # Act
        documents = DocumentRepository.get_by_project(test_session, project.id)

        # Assert
        assert documents == []

    def test_filters_by_project(
        self,
        test_session: Session,
        project_factory,
        document_factory,
    ):
        """Test that get_by_project only returns documents from specified project."""
        # Arrange
        project1 = project_factory(name="Project 1")
        project2 = project_factory(name="Project 2")

        # Documents in project1
        doc1_proj1 = document_factory(text="Doc in Project 1", project_id=project1.id)

        # Documents in project2
        doc1_proj2 = document_factory(text="Doc in Project 2", project_id=project2.id)

        # Act - Get documents from project1
        documents = DocumentRepository.get_by_project(test_session, project1.id)

        # Assert - Should only contain doc from project1
        assert len(documents) == 1
        assert documents[0].id == doc1_proj1.id
        assert documents[0].text == "Doc in Project 1"
