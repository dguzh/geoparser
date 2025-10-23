"""
Unit tests for geoparser/db/models/recognition.py

Tests the Recognition model.
"""

import uuid

import pytest
from sqlmodel import Session

from geoparser.db.models import RecognitionCreate, RecognitionUpdate


@pytest.mark.unit
class TestRecognitionModel:
    """Test the Recognition model."""

    def test_creates_recognition_with_valid_data(
        self, test_session: Session, document_factory, recognizer_factory
    ):
        """Test that a Recognition can be created with valid data."""
        # Arrange
        from geoparser.db.models import Recognition

        document = document_factory()
        recognizer = recognizer_factory(id="test_recognizer")

        recognition = Recognition(document_id=document.id, recognizer_id=recognizer.id)

        # Act
        test_session.add(recognition)
        test_session.commit()
        test_session.refresh(recognition)

        # Assert
        assert recognition.id is not None
        assert isinstance(recognition.id, uuid.UUID)
        assert recognition.document_id == document.id
        assert recognition.recognizer_id == recognizer.id

    def test_generates_uuid_automatically(
        self, test_session: Session, document_factory, recognizer_factory
    ):
        """Test that Recognition automatically generates a UUID for id."""
        # Arrange
        from geoparser.db.models import Recognition

        document = document_factory()
        recognizer = recognizer_factory(id="test")

        recognition = Recognition(document_id=document.id, recognizer_id=recognizer.id)

        # Act
        test_session.add(recognition)
        test_session.commit()

        # Assert
        assert recognition.id is not None
        assert isinstance(recognition.id, uuid.UUID)

    def test_has_document_relationship(self, test_session: Session):
        """Test that Recognition has a relationship to document."""
        # Arrange
        from geoparser.db.models import Recognition

        recognition = Recognition(document_id=uuid.uuid4(), recognizer_id="test")

        # Assert
        assert hasattr(recognition, "document")

    def test_has_recognizer_relationship(self, test_session: Session):
        """Test that Recognition has a relationship to recognizer."""
        # Arrange
        from geoparser.db.models import Recognition

        recognition = Recognition(document_id=uuid.uuid4(), recognizer_id="test")

        # Assert
        assert hasattr(recognition, "recognizer")


@pytest.mark.unit
class TestRecognitionCreate:
    """Test the RecognitionCreate model."""

    def test_creates_with_required_fields(self):
        """Test that RecognitionCreate can be created with required fields."""
        # Arrange
        document_id = uuid.uuid4()
        recognizer_id = "test_recognizer"

        # Act
        recognition_create = RecognitionCreate(
            document_id=document_id, recognizer_id=recognizer_id
        )

        # Assert
        assert recognition_create.document_id == document_id
        assert recognition_create.recognizer_id == recognizer_id


@pytest.mark.unit
class TestRecognitionUpdate:
    """Test the RecognitionUpdate model."""

    def test_creates_update_with_all_fields(self):
        """Test that RecognitionUpdate can be created with all fields."""
        # Arrange
        recognition_id = uuid.uuid4()
        document_id = uuid.uuid4()

        # Act
        recognition_update = RecognitionUpdate(
            id=recognition_id,
            document_id=document_id,
            recognizer_id="new_recognizer",
        )

        # Assert
        assert recognition_update.id == recognition_id
        assert recognition_update.document_id == document_id
        assert recognition_update.recognizer_id == "new_recognizer"

    def test_allows_optional_fields(self):
        """Test that RecognitionUpdate allows optional fields."""
        # Arrange
        recognition_id = uuid.uuid4()

        # Act
        recognition_update = RecognitionUpdate(id=recognition_id)

        # Assert
        assert recognition_update.id == recognition_id
        assert recognition_update.document_id is None
        assert recognition_update.recognizer_id is None
