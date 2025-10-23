"""
Unit tests for geoparser/services/recognition.py

Tests the RecognitionService class with mocked recognizers.
"""

from unittest.mock import patch

import pytest

from geoparser.services.recognition import RecognitionService


@pytest.mark.unit
class TestRecognitionServiceInitialization:
    """Test RecognitionService initialization."""

    def test_creates_with_recognizer(self, mock_spacy_recognizer):
        """Test that RecognitionService can be created with a recognizer."""
        # Arrange & Act
        service = RecognitionService(mock_spacy_recognizer)

        # Assert
        assert service.recognizer == mock_spacy_recognizer


@pytest.mark.unit
class TestRecognitionServicePredict:
    """Test RecognitionService predict method."""

    def test_ensures_recognizer_record_exists(
        self, test_session, mock_spacy_recognizer, document_factory
    ):
        """Test that predict ensures recognizer record exists in database."""
        # Arrange
        document = document_factory(text="Test document")
        mock_spacy_recognizer.predict.return_value = [[(0, 4)]]
        service = RecognitionService(mock_spacy_recognizer)

        # Act
        with patch("geoparser.db.engine.engine"):
            with patch(
                "geoparser.services.recognition.Session", return_value=test_session
            ):
                service.predict([document])

        # Assert - Recognizer record should be created
        from geoparser.db.crud import RecognizerRepository

        recognizer = RecognizerRepository.get(test_session, mock_spacy_recognizer.id)
        assert recognizer is not None
        assert recognizer.id == mock_spacy_recognizer.id

    def test_calls_recognizer_predict(
        self, test_session, mock_spacy_recognizer, document_factory
    ):
        """Test that predict calls the recognizer's predict method."""
        # Arrange
        document = document_factory(text="New York is a city.")
        mock_spacy_recognizer.predict.return_value = [[(0, 8)]]
        service = RecognitionService(mock_spacy_recognizer)

        # Act
        with patch("geoparser.db.engine.engine"):
            with patch(
                "geoparser.services.recognition.Session", return_value=test_session
            ):
                service.predict([document])

        # Assert
        mock_spacy_recognizer.predict.assert_called_once()
        # Check that it was called with the document text
        call_args = mock_spacy_recognizer.predict.call_args[0][0]
        assert call_args == ["New York is a city."]

    def test_creates_references_in_database(
        self, test_session, mock_spacy_recognizer, document_factory
    ):
        """Test that predict creates reference records in the database."""
        # Arrange
        document = document_factory(text="Test document")
        mock_spacy_recognizer.predict.return_value = [[(0, 4), (5, 13)]]
        service = RecognitionService(mock_spacy_recognizer)

        # Act
        with patch("geoparser.db.engine.engine"):
            with patch(
                "geoparser.services.recognition.Session", return_value=test_session
            ):
                service.predict([document])

        # Assert - References should be created
        from sqlmodel import select

        from geoparser.db.models import Reference

        statement = select(Reference).where(Reference.document_id == document.id)
        references = test_session.exec(statement).unique().all()
        assert len(references) == 2
        assert references[0].start == 0
        assert references[0].end == 4
        assert references[1].start == 5
        assert references[1].end == 13

    def test_creates_recognition_record(
        self, test_session, mock_spacy_recognizer, document_factory
    ):
        """Test that predict creates a recognition record marking document as processed."""
        # Arrange
        document = document_factory(text="Test")
        mock_spacy_recognizer.predict.return_value = [[(0, 4)]]
        service = RecognitionService(mock_spacy_recognizer)

        # Act
        with patch("geoparser.db.engine.engine"):
            with patch(
                "geoparser.services.recognition.Session", return_value=test_session
            ):
                service.predict([document])

        # Assert - Recognition record should exist
        from geoparser.db.crud import RecognitionRepository

        recognition = RecognitionRepository.get_by_document_and_recognizer(
            test_session, document.id, mock_spacy_recognizer.id
        )
        assert recognition is not None

    def test_skips_already_processed_documents(
        self, test_session, mock_spacy_recognizer, document_factory, recognizer_factory
    ):
        """Test that predict skips documents already processed by this recognizer."""
        # Arrange
        recognizer_record = recognizer_factory(
            id=mock_spacy_recognizer.id,
            name=mock_spacy_recognizer.name,
            config=mock_spacy_recognizer.config,
        )
        document = document_factory(text="Test")

        # Mark as already processed
        from geoparser.db.crud import RecognitionRepository
        from geoparser.db.models import RecognitionCreate

        RecognitionRepository.create(
            test_session,
            RecognitionCreate(
                document_id=document.id, recognizer_id=recognizer_record.id
            ),
        )

        mock_spacy_recognizer.predict.return_value = [[(0, 4)]]
        service = RecognitionService(mock_spacy_recognizer)

        # Act
        with patch("geoparser.db.engine.engine"):
            with patch(
                "geoparser.services.recognition.Session", return_value=test_session
            ):
                service.predict([document])

        # Assert - Predict should not be called since document was already processed
        mock_spacy_recognizer.predict.assert_not_called()

    def test_handles_none_predictions(
        self, test_session, mock_spacy_recognizer, document_factory
    ):
        """Test that predict handles None predictions (unavailable) correctly."""
        # Arrange
        document = document_factory(text="Test")
        mock_spacy_recognizer.predict.return_value = [None]  # Prediction not available
        service = RecognitionService(mock_spacy_recognizer)

        # Act
        with patch("geoparser.db.engine.engine"):
            with patch(
                "geoparser.services.recognition.Session", return_value=test_session
            ):
                service.predict([document])

        # Assert - No references should be created, no recognition record
        from sqlmodel import select

        from geoparser.db.crud import RecognitionRepository
        from geoparser.db.models import Reference

        statement = select(Reference).where(Reference.document_id == document.id)
        references = test_session.exec(statement).all()
        assert len(references) == 0

        recognition = RecognitionRepository.get_by_document_and_recognizer(
            test_session, document.id, mock_spacy_recognizer.id
        )
        assert recognition is None

    def test_handles_empty_document_list(self, mock_spacy_recognizer):
        """Test that predict handles empty document list gracefully."""
        # Arrange
        service = RecognitionService(mock_spacy_recognizer)

        # Act
        service.predict([])

        # Assert - Should not call predict on recognizer
        mock_spacy_recognizer.predict.assert_not_called()

    def test_processes_multiple_documents(
        self, test_session, mock_spacy_recognizer, document_factory
    ):
        """Test that predict handles multiple documents correctly."""
        # Arrange
        doc1 = document_factory(text="New York")
        doc2 = document_factory(text="Paris")
        mock_spacy_recognizer.predict.return_value = [[(0, 8)], [(0, 5)]]
        service = RecognitionService(mock_spacy_recognizer)

        # Act
        with patch("geoparser.db.engine.engine"):
            with patch(
                "geoparser.services.recognition.Session", return_value=test_session
            ):
                service.predict([doc1, doc2])

        # Assert - Both documents should have references
        from sqlmodel import select

        from geoparser.db.models import Reference

        statement1 = select(Reference).where(Reference.document_id == doc1.id)
        refs1 = test_session.exec(statement1).unique().all()
        assert len(refs1) == 1

        statement2 = select(Reference).where(Reference.document_id == doc2.id)
        refs2 = test_session.exec(statement2).unique().all()
        assert len(refs2) == 1
