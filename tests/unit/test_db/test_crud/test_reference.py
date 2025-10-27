"""
Unit tests for geoparser/db/crud/reference.py

Tests the ReferenceRepository class with custom query methods.
"""

import pytest
from sqlmodel import Session

from geoparser.db.crud import ReferenceRepository
from geoparser.db.models import ReferenceUpdate


@pytest.mark.unit
class TestReferenceRepositoryUpdate:
    """Test the update method of ReferenceRepository."""

    def test_updates_reference_and_refreshes_text(
        self,
        test_session: Session,
        reference_factory,
        document_factory,
    ):
        """Test that update refreshes the text field when positions change."""
        # Arrange
        document = document_factory(text="Hello World, this is a test.")
        reference = reference_factory(
            start=0, end=5, document_id=document.id
        )  # "Hello"

        # Verify initial state
        test_session.refresh(reference)
        assert reference.text == "Hello"

        # Act - Update to point to "World"
        update = ReferenceUpdate(id=reference.id, start=6, end=11)
        updated_ref = ReferenceRepository.update(
            test_session, db_obj=reference, obj_in=update
        )

        # Assert - Text should be updated to "World"
        test_session.refresh(updated_ref)
        assert updated_ref.text == "World"
        assert updated_ref.start == 6
        assert updated_ref.end == 11

    def test_updates_text_when_document_changes(
        self,
        test_session: Session,
        reference_factory,
        document_factory,
    ):
        """Test that update refreshes text when document_id changes."""
        # Arrange
        doc1 = document_factory(text="First document text")
        doc2 = document_factory(text="Second document text")
        reference = reference_factory(start=0, end=5, document_id=doc1.id)  # "First"

        test_session.refresh(reference)
        assert reference.text == "First"

        # Act - Update to point to second document
        update = ReferenceUpdate(id=reference.id, document_id=doc2.id, start=0, end=6)
        updated_ref = ReferenceRepository.update(
            test_session, db_obj=reference, obj_in=update
        )

        # Assert - Text should be from second document
        test_session.refresh(updated_ref)
        assert updated_ref.text == "Second"
        assert updated_ref.document_id == doc2.id


@pytest.mark.unit
class TestReferenceRepositoryGetByDocument:
    """Test the get_by_document method of ReferenceRepository."""

    def test_returns_references_for_document(
        self,
        test_session: Session,
        document_factory,
        reference_factory,
    ):
        """Test that get_by_document returns all references for a document."""
        # Arrange
        document = document_factory(text="New York and Paris are cities.")
        ref1 = reference_factory(start=0, end=8, document_id=document.id)  # "New York"
        ref2 = reference_factory(start=13, end=18, document_id=document.id)  # "Paris"

        # Act
        references = ReferenceRepository.get_by_document(test_session, document.id)

        # Assert
        assert len(references) == 2
        reference_ids = [r.id for r in references]
        assert ref1.id in reference_ids
        assert ref2.id in reference_ids

    def test_returns_empty_list_for_document_without_references(
        self, test_session: Session, document_factory
    ):
        """Test that get_by_document returns empty list for document without references."""
        # Arrange
        document = document_factory()

        # Act
        references = ReferenceRepository.get_by_document(test_session, document.id)

        # Assert
        assert references == []


@pytest.mark.unit
class TestReferenceRepositoryGetByDocumentAndSpan:
    """Test the get_by_document_and_span method of ReferenceRepository."""

    def test_returns_reference_for_matching_span(
        self,
        test_session: Session,
        document_factory,
        reference_factory,
    ):
        """Test that get_by_document_and_span returns reference for matching document and span."""
        # Arrange
        document = document_factory(text="New York is a city")
        reference = reference_factory(start=0, end=8, document_id=document.id)

        # Act
        found_ref = ReferenceRepository.get_by_document_and_span(
            test_session, document.id, 0, 8
        )

        # Assert
        assert found_ref is not None
        assert found_ref.id == reference.id
        assert found_ref.start == 0
        assert found_ref.end == 8

    def test_returns_none_for_non_matching_span(
        self,
        test_session: Session,
        document_factory,
        reference_factory,
    ):
        """Test that get_by_document_and_span returns None for non-matching span."""
        # Arrange
        document = document_factory(text="New York is a city")
        reference = reference_factory(start=0, end=8, document_id=document.id)

        # Act - Query with different span
        found_ref = ReferenceRepository.get_by_document_and_span(
            test_session, document.id, 9, 11
        )

        # Assert
        assert found_ref is None

    def test_distinguishes_between_different_spans_in_same_document(
        self,
        test_session: Session,
        document_factory,
        reference_factory,
    ):
        """Test that method can distinguish between different spans in the same document."""
        # Arrange
        document = document_factory(text="New York and Paris are cities")
        ref1 = reference_factory(start=0, end=8, document_id=document.id)
        ref2 = reference_factory(start=13, end=18, document_id=document.id)

        # Act - Query for first span
        found_ref1 = ReferenceRepository.get_by_document_and_span(
            test_session, document.id, 0, 8
        )
        # Query for second span
        found_ref2 = ReferenceRepository.get_by_document_and_span(
            test_session, document.id, 13, 18
        )

        # Assert
        assert found_ref1 is not None
        assert found_ref2 is not None
        assert found_ref1.id == ref1.id
        assert found_ref2.id == ref2.id
        assert found_ref1.id != found_ref2.id
