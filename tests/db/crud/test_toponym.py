import uuid

from sqlmodel import Session as DBSession

from geoparser.db.crud import ToponymRepository
from geoparser.db.models import Document, Toponym, ToponymCreate, ToponymUpdate


def test_create(test_db: DBSession, test_document: Document):
    """Test creating a toponym."""
    # Create a toponym using the create model with all required fields
    toponym_create = ToponymCreate(start=10, end=15, document_id=test_document.id)

    # Create the toponym
    created_toponym = ToponymRepository.create(test_db, toponym_create)

    assert created_toponym.id is not None
    assert created_toponym.start == 10
    assert created_toponym.end == 15
    assert created_toponym.document_id == test_document.id

    # Verify it was saved to the database
    db_toponym = test_db.get(Toponym, created_toponym.id)
    assert db_toponym is not None
    assert db_toponym.start == 10
    assert db_toponym.end == 15
    assert db_toponym.document_id == test_document.id


def test_get(test_db: DBSession, test_toponym: Toponym):
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


def test_get_by_document(
    test_db: DBSession, test_document: Document, test_toponym: Toponym
):
    """Test getting toponyms by document ID."""
    # Create another toponym in the same document
    toponym_create = ToponymCreate(start=20, end=25, document_id=test_document.id)

    # Create the toponym
    ToponymRepository.create(test_db, toponym_create)

    # Get toponyms by document
    toponyms = ToponymRepository.get_by_document(test_db, test_document.id)
    assert len(toponyms) == 2
    assert any(t.start == 27 and t.end == 33 for t in toponyms)
    assert any(t.start == 20 and t.end == 25 for t in toponyms)

    # Test with invalid document ID
    invalid_id = uuid.uuid4()
    toponyms = ToponymRepository.get_by_document(test_db, invalid_id)
    assert len(toponyms) == 0


def test_get_all(test_db: DBSession, test_toponym: Toponym):
    """Test getting all toponyms."""
    # Create another toponym
    toponym_create = ToponymCreate(
        start=20, end=25, document_id=test_toponym.document_id
    )

    # Create the toponym
    ToponymRepository.create(test_db, toponym_create)

    # Get all toponyms
    toponyms = ToponymRepository.get_all(test_db)
    assert len(toponyms) == 2
    assert any(t.start == 27 and t.end == 33 for t in toponyms)
    assert any(t.start == 20 and t.end == 25 for t in toponyms)


def test_update(test_db: DBSession, test_toponym: Toponym):
    """Test updating a toponym."""
    # Update the toponym
    toponym_update = ToponymUpdate(id=test_toponym.id, start=40, end=45)
    updated_toponym = ToponymRepository.update(
        test_db, db_obj=test_toponym, obj_in=toponym_update
    )

    assert updated_toponym.id == test_toponym.id
    assert updated_toponym.start == 40
    assert updated_toponym.end == 45

    # Verify it was updated in the database
    db_toponym = test_db.get(Toponym, test_toponym.id)
    assert db_toponym is not None
    assert db_toponym.start == 40
    assert db_toponym.end == 45


def test_delete(test_db: DBSession, test_toponym: Toponym):
    """Test deleting a toponym."""
    # Delete the toponym
    deleted_toponym = ToponymRepository.delete(test_db, id=test_toponym.id)

    assert deleted_toponym is not None
    assert deleted_toponym.id == test_toponym.id

    # Verify it was deleted from the database
    db_toponym = test_db.get(Toponym, test_toponym.id)
    assert db_toponym is None
