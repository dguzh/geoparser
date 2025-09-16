import uuid

from sqlmodel import Session

from geoparser.db.crud import ReferenceRepository
from geoparser.db.models import (
    Document,
    Recognizer,
    Reference,
    ReferenceCreate,
    ReferenceUpdate,
)


def test_create(test_db: Session, test_document: Document, test_recognizer: Recognizer):
    """Test creating a reference."""
    # Create a reference using the create model with all required fields
    reference_create = ReferenceCreate(
        start=29, end=35, document_id=test_document.id, recognizer_id=test_recognizer.id
    )

    # Create the reference
    created_reference = ReferenceRepository.create(test_db, reference_create)

    assert created_reference.id is not None
    assert created_reference.start == 29
    assert created_reference.end == 35
    assert created_reference.document_id == test_document.id
    # Verify text field is correctly populated based on document content
    assert created_reference.text == test_document.text[29:35]

    # Verify it was saved to the database
    db_reference = test_db.get(Reference, created_reference.id)
    assert db_reference is not None
    assert db_reference.start == 29
    assert db_reference.end == 35
    assert db_reference.document_id == test_document.id
    assert db_reference.text == test_document.text[29:35]


def test_get(test_db: Session, test_reference: Reference):
    """Test getting a reference by ID."""
    # Test with valid ID
    reference = ReferenceRepository.get(test_db, test_reference.id)
    assert reference is not None
    assert reference.id == test_reference.id
    assert reference.start == test_reference.start
    assert reference.end == test_reference.end

    # Test with invalid ID
    invalid_id = uuid.uuid4()
    reference = ReferenceRepository.get(test_db, invalid_id)
    assert reference is None


def test_get_by_document_and_span(
    test_db: Session, test_document: Document, test_reference: Reference
):
    """Test getting a reference by document ID and span."""
    # Test with valid document ID and span
    reference = ReferenceRepository.get_by_document_and_span(
        test_db, test_document.id, test_reference.start, test_reference.end
    )
    assert reference is not None
    assert reference.id == test_reference.id
    assert reference.start == test_reference.start
    assert reference.end == test_reference.end

    # Test with valid document ID but invalid span
    reference = ReferenceRepository.get_by_document_and_span(
        test_db, test_document.id, 999, 1000
    )
    assert reference is None

    # Test with invalid document ID
    invalid_id = uuid.uuid4()
    reference = ReferenceRepository.get_by_document_and_span(
        test_db, invalid_id, test_reference.start, test_reference.end
    )
    assert reference is None


def test_get_by_document(
    test_db: Session,
    test_document: Document,
    test_reference: Reference,
    test_recognizer: Recognizer,
):
    """Test getting references by document ID."""
    # Create another reference in the same document
    reference_create = ReferenceCreate(
        start=10, end=14, document_id=test_document.id, recognizer_id=test_recognizer.id
    )

    # Create the reference
    created_reference = ReferenceRepository.create(test_db, reference_create)

    # Verify text field is populated
    assert created_reference.text == test_document.text[10:14]

    # Get references by document
    references = ReferenceRepository.get_by_document(test_db, test_document.id)
    assert len(references) == 2
    assert any(
        r.start == 29 and r.end == 35 and r.text == test_document.text[29:35]
        for r in references
    )
    assert any(
        r.start == 10 and r.end == 14 and r.text == test_document.text[10:14]
        for r in references
    )

    # Test with invalid document ID
    invalid_id = uuid.uuid4()
    references = ReferenceRepository.get_by_document(test_db, invalid_id)
    assert len(references) == 0


def test_get_all(test_db: Session, test_reference: Reference):
    """Test getting all references."""
    # Get document text for verification
    document = test_db.get(Document, test_reference.document_id)

    # Create another reference
    reference_create = ReferenceCreate(
        start=10,
        end=14,
        document_id=test_reference.document_id,
        recognizer_id=test_reference.recognizer_id,
    )

    # Create the reference
    created_reference = ReferenceRepository.create(test_db, reference_create)

    # Verify text field is populated
    assert created_reference.text == document.text[10:14]

    # Get all references
    references = ReferenceRepository.get_all(test_db)
    assert len(references) == 2
    assert any(
        r.start == 29 and r.end == 35 and r.text == document.text[29:35]
        for r in references
    )
    assert any(
        r.start == 10 and r.end == 14 and r.text == document.text[10:14]
        for r in references
    )


def test_update(test_db: Session, test_reference: Reference):
    """Test updating a reference."""
    # Update the reference
    reference_update = ReferenceUpdate(id=test_reference.id, start=10, end=14)
    updated_reference = ReferenceRepository.update(
        test_db, db_obj=test_reference, obj_in=reference_update
    )

    assert updated_reference.id == test_reference.id
    assert updated_reference.start == 10
    assert updated_reference.end == 14
    # Verify text is updated
    document = test_db.get(Document, test_reference.document_id)
    assert updated_reference.text == document.text[10:14]

    # Verify it was updated in the database
    db_reference = test_db.get(Reference, test_reference.id)
    assert db_reference is not None
    assert db_reference.start == 10
    assert db_reference.end == 14
    assert db_reference.text == document.text[10:14]


def test_delete(test_db: Session, test_reference: Reference):
    """Test deleting a reference."""
    # Delete the reference
    deleted_reference = ReferenceRepository.delete(test_db, id=test_reference.id)

    assert deleted_reference is not None
    assert deleted_reference.id == test_reference.id

    # Verify it was deleted from the database
    db_reference = test_db.get(Reference, test_reference.id)
    assert db_reference is None
