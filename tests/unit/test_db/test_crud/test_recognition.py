"""
Unit tests for geoparser/db/crud/recognition.py

Tests the RecognitionRepository class with custom query methods.
"""

import pytest
from sqlmodel import Session

from geoparser.db.crud import RecognitionRepository
from geoparser.db.models import RecognitionCreate


@pytest.mark.unit
class TestRecognitionRepositoryGetByDocument:
    """Test the get_by_document method of RecognitionRepository."""

    def test_returns_recognitions_for_document(
        self,
        test_session: Session,
        document_factory,
        recognizer_factory,
    ):
        """Test that get_by_document returns all recognitions for a document."""
        # Arrange
        document = document_factory()
        recognizer1 = recognizer_factory(id="rec1")
        recognizer2 = recognizer_factory(id="rec2")

        RecognitionRepository.create(
            test_session,
            RecognitionCreate(document_id=document.id, recognizer_id="rec1"),
        )
        RecognitionRepository.create(
            test_session,
            RecognitionCreate(document_id=document.id, recognizer_id="rec2"),
        )

        # Act
        recognitions = RecognitionRepository.get_by_document(test_session, document.id)

        # Assert
        assert len(recognitions) == 2
        recognizer_ids = [r.recognizer_id for r in recognitions]
        assert "rec1" in recognizer_ids
        assert "rec2" in recognizer_ids

    def test_returns_empty_list_for_document_without_recognitions(
        self, test_session: Session, document_factory
    ):
        """Test that get_by_document returns empty list for document without recognitions."""
        # Arrange
        document = document_factory()

        # Act
        recognitions = RecognitionRepository.get_by_document(test_session, document.id)

        # Assert
        assert recognitions == []


@pytest.mark.unit
class TestRecognitionRepositoryGetByRecognizer:
    """Test the get_by_recognizer method of RecognitionRepository."""

    def test_returns_recognitions_for_recognizer(
        self,
        test_session: Session,
        document_factory,
        recognizer_factory,
    ):
        """Test that get_by_recognizer returns all recognitions for a recognizer."""
        # Arrange
        recognizer = recognizer_factory(id="test_rec")
        doc1 = document_factory()
        doc2 = document_factory()

        RecognitionRepository.create(
            test_session,
            RecognitionCreate(document_id=doc1.id, recognizer_id="test_rec"),
        )
        RecognitionRepository.create(
            test_session,
            RecognitionCreate(document_id=doc2.id, recognizer_id="test_rec"),
        )

        # Act
        recognitions = RecognitionRepository.get_by_recognizer(test_session, "test_rec")

        # Assert
        assert len(recognitions) == 2
        document_ids = [r.document_id for r in recognitions]
        assert doc1.id in document_ids
        assert doc2.id in document_ids

    def test_returns_empty_list_for_recognizer_without_recognitions(
        self, test_session: Session, recognizer_factory
    ):
        """Test that get_by_recognizer returns empty list for recognizer without recognitions."""
        # Arrange
        recognizer = recognizer_factory(id="test_rec")

        # Act
        recognitions = RecognitionRepository.get_by_recognizer(test_session, "test_rec")

        # Assert
        assert recognitions == []


@pytest.mark.unit
class TestRecognitionRepositoryGetByDocumentAndRecognizer:
    """Test the get_by_document_and_recognizer method of RecognitionRepository."""

    def test_returns_recognition_for_matching_pair(
        self,
        test_session: Session,
        document_factory,
        recognizer_factory,
    ):
        """Test that get_by_document_and_recognizer returns recognition for matching pair."""
        # Arrange
        document = document_factory()
        recognizer = recognizer_factory(id="test_rec")

        created_recognition = RecognitionRepository.create(
            test_session,
            RecognitionCreate(document_id=document.id, recognizer_id="test_rec"),
        )

        # Act
        recognition = RecognitionRepository.get_by_document_and_recognizer(
            test_session, document.id, "test_rec"
        )

        # Assert
        assert recognition is not None
        assert recognition.id == created_recognition.id
        assert recognition.document_id == document.id
        assert recognition.recognizer_id == "test_rec"

    def test_returns_none_for_non_matching_pair(
        self,
        test_session: Session,
        document_factory,
        recognizer_factory,
    ):
        """Test that get_by_document_and_recognizer returns None for non-matching pair."""
        # Arrange
        document = document_factory()
        recognizer = recognizer_factory(id="test_rec")

        # Act
        recognition = RecognitionRepository.get_by_document_and_recognizer(
            test_session, document.id, "test_rec"
        )

        # Assert
        assert recognition is None


@pytest.mark.unit
class TestRecognitionRepositoryGetUnprocessedDocuments:
    """Test the get_unprocessed_documents method of RecognitionRepository."""

    def test_returns_documents_not_processed_by_recognizer(
        self,
        test_session: Session,
        project_factory,
        document_factory,
        recognizer_factory,
    ):
        """Test that get_unprocessed_documents returns documents not yet processed."""
        # Arrange
        project = project_factory()
        recognizer = recognizer_factory(id="test_rec")

        # Create three documents
        doc1 = document_factory(project_id=project.id)
        doc2 = document_factory(project_id=project.id)
        doc3 = document_factory(project_id=project.id)

        # Mark doc1 as processed
        RecognitionRepository.create(
            test_session,
            RecognitionCreate(document_id=doc1.id, recognizer_id="test_rec"),
        )

        # Act
        unprocessed = RecognitionRepository.get_unprocessed_documents(
            test_session, project.id, "test_rec"
        )

        # Assert
        assert len(unprocessed) == 2
        unprocessed_ids = [d.id for d in unprocessed]
        assert doc1.id not in unprocessed_ids
        assert doc2.id in unprocessed_ids
        assert doc3.id in unprocessed_ids

    def test_returns_all_documents_when_none_processed(
        self,
        test_session: Session,
        project_factory,
        document_factory,
        recognizer_factory,
    ):
        """Test that get_unprocessed_documents returns all documents when none processed."""
        # Arrange
        project = project_factory()
        recognizer = recognizer_factory(id="test_rec")

        doc1 = document_factory(project_id=project.id)
        doc2 = document_factory(project_id=project.id)

        # Act
        unprocessed = RecognitionRepository.get_unprocessed_documents(
            test_session, project.id, "test_rec"
        )

        # Assert
        assert len(unprocessed) == 2

    def test_returns_empty_list_when_all_processed(
        self,
        test_session: Session,
        project_factory,
        document_factory,
        recognizer_factory,
    ):
        """Test that get_unprocessed_documents returns empty list when all processed."""
        # Arrange
        project = project_factory()
        recognizer = recognizer_factory(id="test_rec")

        doc1 = document_factory(project_id=project.id)
        doc2 = document_factory(project_id=project.id)

        # Mark both as processed
        RecognitionRepository.create(
            test_session,
            RecognitionCreate(document_id=doc1.id, recognizer_id="test_rec"),
        )
        RecognitionRepository.create(
            test_session,
            RecognitionCreate(document_id=doc2.id, recognizer_id="test_rec"),
        )

        # Act
        unprocessed = RecognitionRepository.get_unprocessed_documents(
            test_session, project.id, "test_rec"
        )

        # Assert
        assert unprocessed == []

    def test_filters_by_project(
        self,
        test_session: Session,
        project_factory,
        document_factory,
        recognizer_factory,
    ):
        """Test that get_unprocessed_documents only returns documents from specified project."""
        # Arrange
        project1 = project_factory()
        project2 = project_factory()
        recognizer = recognizer_factory(id="test_rec")

        # Documents in project1
        doc1_proj1 = document_factory(project_id=project1.id)

        # Documents in project2
        doc1_proj2 = document_factory(project_id=project2.id)

        # Act - Get unprocessed from project1
        unprocessed = RecognitionRepository.get_unprocessed_documents(
            test_session, project1.id, "test_rec"
        )

        # Assert - Should only contain doc from project1
        assert len(unprocessed) == 1
        assert unprocessed[0].id == doc1_proj1.id
