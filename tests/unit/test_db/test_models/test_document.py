"""
Unit tests for geoparser/db/models/document.py

Tests the Document model, including text storage, context filtering,
and the toponyms property.
"""

import uuid

import pytest
from sqlmodel import Session

from geoparser.db.models import DocumentCreate, DocumentUpdate


@pytest.mark.unit
class TestDocumentModel:
    """Test the Document model."""

    def test_creates_document_with_valid_data(
        self, test_session: Session, document_factory
    ):
        """Test that a Document can be created with valid data."""
        # Arrange & Act
        document = document_factory(text="Test document text.")

        # Assert
        assert document.id is not None
        assert isinstance(document.id, uuid.UUID)
        assert document.text == "Test document text."
        assert document.project_id is not None

    def test_has_project_relationship(
        self, test_session: Session, document_factory, project_factory
    ):
        """Test that Document has a relationship to its project."""
        # Arrange
        project = project_factory(name="Parent Project")
        document = document_factory(text="Test", project_id=project.id)

        # Act
        test_session.refresh(document)

        # Assert
        assert document.project is not None
        assert document.project.name == "Parent Project"

    def test_has_references_relationship(self, test_session: Session, document_factory):
        """Test that Document has a relationship to references."""
        # Arrange
        document = document_factory(text="Test document")

        # Assert
        assert hasattr(document, "references")
        assert isinstance(document.references, list)

    def test_references_ordered_by_start_position(
        self, test_session: Session, document_factory, reference_factory
    ):
        """Test that references are ordered by start position."""
        # Arrange
        document = document_factory(text="New York and Paris are cities.")

        # Create references in reverse order
        ref2 = reference_factory(start=13, end=18, document_id=document.id)  # Paris
        ref1 = reference_factory(start=0, end=8, document_id=document.id)  # New York

        # Act
        test_session.refresh(document)

        # Assert - References should be ordered by start position
        assert len(document.references) == 2
        assert document.references[0].start == 0
        assert document.references[1].start == 13

    def test_set_recognizer_context(self, test_session: Session, document_factory):
        """Test that _set_recognizer_context sets the internal context variable."""
        # Arrange
        document = document_factory()
        recognizer_id = "test_recognizer_id"

        # Act
        document._set_recognizer_context(recognizer_id)

        # Assert
        assert document._recognizer_id == recognizer_id

    def test_toponyms_returns_empty_list_when_no_context(
        self, test_session: Session, document_factory, reference_factory
    ):
        """Test that toponyms returns empty list when no recognizer context is set."""
        # Arrange
        document = document_factory()
        reference_factory(document_id=document.id)
        test_session.refresh(document)

        # Act
        toponyms = document.toponyms

        # Assert
        assert toponyms == []

    def test_toponyms_filters_by_recognizer_context(
        self,
        test_session: Session,
        document_factory,
        reference_factory,
        recognizer_factory,
    ):
        """Test that toponyms property filters references by recognizer context."""
        # Arrange
        document = document_factory(text="Test document")
        recognizer1 = recognizer_factory(id="rec1", name="Recognizer 1")
        recognizer2 = recognizer_factory(id="rec2", name="Recognizer 2")

        ref1 = reference_factory(
            start=0, end=4, document_id=document.id, recognizer_id="rec1"
        )
        ref2 = reference_factory(
            start=5, end=13, document_id=document.id, recognizer_id="rec2"
        )
        ref3 = reference_factory(
            start=0, end=4, document_id=document.id, recognizer_id="rec1"
        )

        test_session.refresh(document)

        # Act - Set context to recognizer1
        document._set_recognizer_context("rec1")
        toponyms_rec1 = document.toponyms

        # Assert - Only references from recognizer1
        assert len(toponyms_rec1) == 2
        assert all(ref.recognizer_id == "rec1" for ref in toponyms_rec1)

        # Act - Set context to recognizer2
        document._set_recognizer_context("rec2")
        toponyms_rec2 = document.toponyms

        # Assert - Only references from recognizer2
        assert len(toponyms_rec2) == 1
        assert toponyms_rec2[0].recognizer_id == "rec2"

    def test_str_representation(self, test_session: Session, document_factory):
        """Test that Document has a useful string representation."""
        # Arrange
        document = document_factory(text="Test text")

        # Act
        str_repr = str(document)

        # Assert
        assert "Document" in str_repr
        assert "Test text" in str_repr

    def test_repr_matches_str(self, test_session: Session, document_factory):
        """Test that __repr__ matches __str__."""
        # Arrange
        document = document_factory(text="Test")

        # Act & Assert
        assert repr(document) == str(document)


@pytest.mark.unit
class TestDocumentCreate:
    """Test the DocumentCreate model."""

    def test_creates_with_text_and_project_id(self):
        """Test that DocumentCreate can be created with text and project_id."""
        # Arrange
        project_id = uuid.uuid4()

        # Act
        document_create = DocumentCreate(text="Test text", project_id=project_id)

        # Assert
        assert document_create.text == "Test text"
        assert document_create.project_id == project_id

    def test_normalizes_newlines_on_creation(self):
        """Test that newlines are normalized when creating DocumentCreate."""
        # Arrange & Act
        document_create = DocumentCreate(
            text="Line1\r\nLine2\rLine3", project_id=uuid.uuid4()
        )

        # Assert
        assert document_create.text == "Line1\nLine2\nLine3"


@pytest.mark.unit
class TestDocumentUpdate:
    """Test the DocumentUpdate model."""

    def test_creates_update_with_all_fields(self):
        """Test that DocumentUpdate can be created with all fields."""
        # Arrange
        doc_id = uuid.uuid4()
        project_id = uuid.uuid4()

        # Act
        document_update = DocumentUpdate(
            id=doc_id, text="Updated text", project_id=project_id
        )

        # Assert
        assert document_update.id == doc_id
        assert document_update.text == "Updated text"
        assert document_update.project_id == project_id

    def test_allows_optional_fields(self):
        """Test that DocumentUpdate allows optional fields."""
        # Arrange
        doc_id = uuid.uuid4()

        # Act
        document_update = DocumentUpdate(id=doc_id)

        # Assert
        assert document_update.id == doc_id
        assert document_update.text is None
        assert document_update.project_id is None
