import uuid

import pytest
from sqlmodel import Session as DBSession

from geoparser.db.crud import SessionRepository
from geoparser.db.models import Session, SessionCreate, SessionUpdate


def test_create(test_db: DBSession):
    """Test creating a session."""
    session_create = SessionCreate(name="test-create-session")
    session = Session(name=session_create.name)

    created_session = SessionRepository.create(test_db, session)

    assert created_session.id is not None
    assert created_session.name == "test-create-session"

    # Verify it was saved to the database
    db_session = test_db.get(Session, created_session.id)
    assert db_session is not None
    assert db_session.name == "test-create-session"


def test_get(test_db: DBSession, test_session: Session):
    """Test getting a session by ID."""
    # Test with valid ID
    session = SessionRepository.get(test_db, test_session.id)
    assert session is not None
    assert session.id == test_session.id
    assert session.name == test_session.name

    # Test with invalid ID
    invalid_id = uuid.uuid4()
    session = SessionRepository.get(test_db, invalid_id)
    assert session is None


def test_get_by_name(test_db: DBSession, test_session: Session):
    """Test getting a session by name."""
    # Test with valid name
    session = SessionRepository.get_by_name(test_db, test_session.name)
    assert session is not None
    assert session.id == test_session.id
    assert session.name == test_session.name

    # Test with invalid name
    session = SessionRepository.get_by_name(test_db, "non-existent-session")
    assert session is None


def test_get_all(test_db: DBSession, test_session: Session):
    """Test getting all sessions."""
    # Create another session
    session_create = SessionCreate(name="another-test-session")
    session = Session(name=session_create.name)
    test_db.add(session)
    test_db.commit()

    # Get all sessions
    sessions = SessionRepository.get_all(test_db)
    assert len(sessions) == 2
    assert any(s.name == "test-session" for s in sessions)
    assert any(s.name == "another-test-session" for s in sessions)


def test_update(test_db: DBSession, test_session: Session):
    """Test updating a session."""
    # Update the session
    session_update = SessionUpdate(id=test_session.id, name="updated-session")
    updated_session = SessionRepository.update(
        test_db, db_obj=test_session, obj_in=session_update
    )

    assert updated_session.id == test_session.id
    assert updated_session.name == "updated-session"

    # Verify it was updated in the database
    db_session = test_db.get(Session, test_session.id)
    assert db_session is not None
    assert db_session.name == "updated-session"


def test_delete(test_db: DBSession, test_session: Session):
    """Test deleting a session."""
    # Delete the session
    deleted_session = SessionRepository.delete(test_db, id=test_session.id)

    assert deleted_session is not None
    assert deleted_session.id == test_session.id

    # Verify it was deleted from the database
    db_session = test_db.get(Session, test_session.id)
    assert db_session is None
