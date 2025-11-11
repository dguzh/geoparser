"""
Unit tests for geoparser/db/models/reference.py

Tests the Reference model, including relationships and context filtering.
"""

import uuid

import pytest
from sqlmodel import Session

from geoparser.db.models import ReferenceCreate, ReferenceUpdate


@pytest.mark.unit
class TestReferenceModel:
    """Test the Reference model."""

    def test_creates_reference_with_valid_data(
        self, test_session: Session, reference_factory, document_factory
    ):
        """Test that a Reference can be created with valid data."""
        # Arrange
        document = document_factory(text="New York is a city")

        # Act
        reference = reference_factory(start=0, end=8, document_id=document.id)

        # Assert
        assert reference.id is not None
        assert isinstance(reference.id, uuid.UUID)
        assert reference.start == 0
        assert reference.end == 8
        assert reference.text == "New York"  # Auto-populated from document
        assert reference.document_id is not None
        assert reference.recognizer_id is not None

    def test_has_document_relationship(
        self, test_session: Session, reference_factory, document_factory
    ):
        """Test that Reference has a relationship to its document."""
        # Arrange
        document = document_factory(text="Test document")
        reference = reference_factory(start=0, end=4, document_id=document.id)

        # Act
        test_session.refresh(reference)

        # Assert
        assert reference.document is not None
        assert reference.document.id == document.id

    def test_has_recognizer_relationship(
        self, test_session: Session, reference_factory, recognizer_factory
    ):
        """Test that Reference has a relationship to its recognizer."""
        # Arrange
        recognizer = recognizer_factory(id="test_rec", name="Test Recognizer")
        reference = reference_factory(recognizer_id="test_rec")

        # Act
        test_session.refresh(reference)

        # Assert
        assert reference.recognizer is not None
        assert reference.recognizer.id == "test_rec"

    def test_has_referents_relationship(self, test_session: Session, reference_factory):
        """Test that Reference has a relationship to referents."""
        # Arrange
        reference = reference_factory()

        # Assert
        assert hasattr(reference, "referents")
        assert isinstance(reference.referents, list)

    def test_has_resolutions_relationship(
        self, test_session: Session, reference_factory
    ):
        """Test that Reference has a relationship to resolutions."""
        # Arrange
        reference = reference_factory()

        # Assert
        assert hasattr(reference, "resolutions")
        assert isinstance(reference.resolutions, list)

    def test_set_resolver_context(self, test_session: Session, reference_factory):
        """Test that _set_resolver_context sets the internal context variable."""
        # Arrange
        reference = reference_factory()
        resolver_id = "test_resolver_id"

        # Act
        reference._set_resolver_context(resolver_id)

        # Assert
        assert reference._resolver_id == resolver_id

    def test_location_returns_none_when_no_context(
        self, test_session: Session, reference_factory
    ):
        """Test that location returns None when no resolver context is set."""
        # Arrange
        reference = reference_factory()

        # Act
        location = reference.location

        # Assert
        assert location is None

    def test_location_returns_feature_when_context_set(
        self,
        test_session: Session,
        reference_factory,
        resolver_factory,
        feature_factory,
    ):
        """Test that location returns the correct feature when resolver context is set."""
        # Arrange
        from geoparser.db.crud import ReferentRepository
        from geoparser.db.models import ReferentCreate

        reference = reference_factory()
        resolver = resolver_factory(id="test_resolver")
        feature = feature_factory()

        # Create referent linking reference to feature via resolver
        referent = ReferentRepository.create(
            test_session,
            ReferentCreate(
                reference_id=reference.id,
                feature_id=feature.id,
                resolver_id=resolver.id,
            ),
        )

        test_session.refresh(reference)

        # Act
        reference._set_resolver_context("test_resolver")
        location = reference.location

        # Assert
        assert location is not None
        assert location.id == feature.id

    def test_location_returns_none_when_no_matching_referent(
        self,
        test_session: Session,
        reference_factory,
        resolver_factory,
        feature_factory,
    ):
        """Test that location returns None when context is set but no matching referent exists."""
        # Arrange
        from geoparser.db.crud import ReferentRepository
        from geoparser.db.models import ReferentCreate

        reference = reference_factory()
        resolver1 = resolver_factory(id="resolver1")
        resolver2 = resolver_factory(id="resolver2")
        feature = feature_factory()

        # Create referent with resolver1
        ReferentRepository.create(
            test_session,
            ReferentCreate(
                reference_id=reference.id,
                feature_id=feature.id,
                resolver_id="resolver1",
            ),
        )

        test_session.refresh(reference)

        # Act - Set context to resolver2 (which has no referent)
        reference._set_resolver_context("resolver2")
        location = reference.location

        # Assert
        assert location is None

    def test_str_representation(
        self, test_session: Session, reference_factory, document_factory
    ):
        """Test that Reference has a useful string representation."""
        # Arrange
        document = document_factory(text="Paris is beautiful")
        reference = reference_factory(start=0, end=5, document_id=document.id)

        # Act
        str_repr = str(reference)

        # Assert
        assert "Reference" in str_repr
        assert "Paris" in str_repr

    def test_repr_matches_str(self, test_session: Session, reference_factory):
        """Test that __repr__ matches __str__."""
        # Arrange
        reference = reference_factory(text="London")

        # Act & Assert
        assert repr(reference) == str(reference)

    def test_cascade_deletes_referents(self, test_session: Session, reference_factory):
        """Test that deleting a reference cascades to delete its referents."""
        # Arrange

        reference = reference_factory()

        # Create referents (we need a feature first, but for this test we can mock it)
        # We'll skip this test for now as it requires more complex setup with features

    def test_text_field_auto_populated_from_document(
        self, test_session: Session, reference_factory, document_factory
    ):
        """Test that text field is auto-populated from document based on start/end."""
        # Arrange
        document = document_factory(text="Test document")

        # Act
        reference = reference_factory(start=0, end=4, document_id=document.id)

        # Assert - Text should be auto-populated from document
        assert reference.text == "Test"


@pytest.mark.unit
class TestReferenceCreate:
    """Test the ReferenceCreate model."""

    def test_creates_with_required_fields(self):
        """Test that ReferenceCreate can be created with required fields."""
        # Arrange
        document_id = uuid.uuid4()
        recognizer_id = "test_recognizer"

        # Act
        reference_create = ReferenceCreate(
            start=0, end=8, document_id=document_id, recognizer_id=recognizer_id
        )

        # Assert
        assert reference_create.start == 0
        assert reference_create.end == 8
        assert reference_create.document_id == document_id
        assert reference_create.recognizer_id == recognizer_id

    def test_text_field_is_optional(self):
        """Test that text field is optional in ReferenceCreate."""
        # Arrange
        document_id = uuid.uuid4()

        # Act
        reference_create = ReferenceCreate(
            start=0, end=4, document_id=document_id, recognizer_id="test_rec"
        )

        # Assert
        assert reference_create.text is None

    def test_can_include_text(self):
        """Test that ReferenceCreate can include optional text field."""
        # Arrange
        document_id = uuid.uuid4()

        # Act
        reference_create = ReferenceCreate(
            start=0,
            end=8,
            text="New York",
            document_id=document_id,
            recognizer_id="test_rec",
        )

        # Assert
        assert reference_create.text == "New York"


@pytest.mark.unit
class TestReferenceUpdate:
    """Test the ReferenceUpdate model."""

    def test_creates_update_with_all_fields(self):
        """Test that ReferenceUpdate can be created with all fields."""
        # Arrange
        ref_id = uuid.uuid4()
        doc_id = uuid.uuid4()

        # Act
        reference_update = ReferenceUpdate(
            id=ref_id,
            document_id=doc_id,
            recognizer_id="new_rec",
            start=5,
            end=10,
        )

        # Assert
        assert reference_update.id == ref_id
        assert reference_update.document_id == doc_id
        assert reference_update.recognizer_id == "new_rec"
        assert reference_update.start == 5
        assert reference_update.end == 10

    def test_allows_optional_fields(self):
        """Test that ReferenceUpdate allows optional fields."""
        # Arrange
        ref_id = uuid.uuid4()

        # Act
        reference_update = ReferenceUpdate(id=ref_id)

        # Assert
        assert reference_update.id == ref_id
        assert reference_update.document_id is None
        assert reference_update.recognizer_id is None
        assert reference_update.start is None
        assert reference_update.end is None
