import uuid

from sqlmodel import Session

from geoparser.db.crud import ToponymRepository
from geoparser.db.models import Document, Toponym, ToponymCreate, ToponymUpdate


def test_create(test_db: Session, test_document: Document):
    """Test creating a toponym."""
    # Create a toponym using the create model with all required fields
    toponym_create = ToponymCreate(start=29, end=35, document_id=test_document.id)

    # Create the toponym
    created_toponym = ToponymRepository.create(test_db, toponym_create)

    assert created_toponym.id is not None
    assert created_toponym.start == 29
    assert created_toponym.end == 35
    assert created_toponym.document_id == test_document.id
    # Verify text field is correctly populated based on document content
    assert created_toponym.text == test_document.text[29:35]

    # Verify it was saved to the database
    db_toponym = test_db.get(Toponym, created_toponym.id)
    assert db_toponym is not None
    assert db_toponym.start == 29
    assert db_toponym.end == 35
    assert db_toponym.document_id == test_document.id
    assert db_toponym.text == test_document.text[29:35]


def test_get(test_db: Session, test_toponym: Toponym):
    """Test getting a toponym by ID."""
    # Test with valid ID
    toponym = ToponymRepository.get(test_db, test_toponym.id)
    assert toponym is not None
    assert toponym.id == test_toponym.id
    assert toponym.start == test_toponym.start
    assert toponym.end == test_toponym.end

    # Test with invalid ID
    invalid_id = uuid.uuid4()
    toponym = ToponymRepository.get(test_db, invalid_id)
    assert toponym is None


def test_get_by_document_and_span(
    test_db: Session, test_document: Document, test_toponym: Toponym
):
    """Test getting a toponym by document ID and span."""
    # Test with valid document ID and span
    toponym = ToponymRepository.get_by_document_and_span(
        test_db, test_document.id, test_toponym.start, test_toponym.end
    )
    assert toponym is not None
    assert toponym.id == test_toponym.id
    assert toponym.start == test_toponym.start
    assert toponym.end == test_toponym.end

    # Test with valid document ID but invalid span
    toponym = ToponymRepository.get_by_document_and_span(
        test_db, test_document.id, 999, 1000
    )
    assert toponym is None

    # Test with invalid document ID
    invalid_id = uuid.uuid4()
    toponym = ToponymRepository.get_by_document_and_span(
        test_db, invalid_id, test_toponym.start, test_toponym.end
    )
    assert toponym is None


def test_get_by_document(
    test_db: Session, test_document: Document, test_toponym: Toponym
):
    """Test getting toponyms by document ID."""
    # Create another toponym in the same document
    toponym_create = ToponymCreate(start=10, end=14, document_id=test_document.id)

    # Create the toponym
    created_toponym = ToponymRepository.create(test_db, toponym_create)

    # Verify text field is populated
    assert created_toponym.text == test_document.text[10:14]

    # Get toponyms by document
    toponyms = ToponymRepository.get_by_document(test_db, test_document.id)
    assert len(toponyms) == 2
    assert any(
        t.start == 29 and t.end == 35 and t.text == test_document.text[29:35]
        for t in toponyms
    )
    assert any(
        t.start == 10 and t.end == 14 and t.text == test_document.text[10:14]
        for t in toponyms
    )

    # Test with invalid document ID
    invalid_id = uuid.uuid4()
    toponyms = ToponymRepository.get_by_document(test_db, invalid_id)
    assert len(toponyms) == 0


def test_get_all(test_db: Session, test_toponym: Toponym):
    """Test getting all toponyms."""
    # Get document text for verification
    document = test_db.get(Document, test_toponym.document_id)

    # Create another toponym
    toponym_create = ToponymCreate(
        start=10, end=14, document_id=test_toponym.document_id
    )

    # Create the toponym
    created_toponym = ToponymRepository.create(test_db, toponym_create)

    # Verify text field is populated
    assert created_toponym.text == document.text[10:14]

    # Get all toponyms
    toponyms = ToponymRepository.get_all(test_db)
    assert len(toponyms) == 2
    assert any(
        t.start == 29 and t.end == 35 and t.text == document.text[29:35]
        for t in toponyms
    )
    assert any(
        t.start == 10 and t.end == 14 and t.text == document.text[10:14]
        for t in toponyms
    )


def test_update(test_db: Session, test_toponym: Toponym):
    """Test updating a toponym."""
    # Update the toponym
    toponym_update = ToponymUpdate(id=test_toponym.id, start=10, end=14)
    updated_toponym = ToponymRepository.update(
        test_db, db_obj=test_toponym, obj_in=toponym_update
    )

    assert updated_toponym.id == test_toponym.id
    assert updated_toponym.start == 10
    assert updated_toponym.end == 14
    # Verify text is updated
    document = test_db.get(Document, test_toponym.document_id)
    assert updated_toponym.text == document.text[10:14]

    # Verify it was updated in the database
    db_toponym = test_db.get(Toponym, test_toponym.id)
    assert db_toponym is not None
    assert db_toponym.start == 10
    assert db_toponym.end == 14
    assert db_toponym.text == document.text[10:14]


def test_delete(test_db: Session, test_toponym: Toponym):
    """Test deleting a toponym."""
    # Delete the toponym
    deleted_toponym = ToponymRepository.delete(test_db, id=test_toponym.id)

    assert deleted_toponym is not None
    assert deleted_toponym.id == test_toponym.id

    # Verify it was deleted from the database
    db_toponym = test_db.get(Toponym, test_toponym.id)
    assert db_toponym is None
