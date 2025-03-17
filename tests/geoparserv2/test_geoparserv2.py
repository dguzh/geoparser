import uuid
from unittest.mock import patch, MagicMock

import pytest
from sqlmodel import Session as DBSession

from geoparser.db.crud import SessionRepository, DocumentRepository
from geoparser.db.models import Session, Document
from geoparser.geoparserv2.geoparserv2 import GeoparserV2


def test_load_session_existing(test_db: DBSession, test_session: Session):
    """Test loading an existing session."""
    geoparserv2 = GeoparserV2.__new__(GeoparserV2)  # Create instance without calling __init__
    
    # Call load_session directly
    session = geoparserv2.load_session(test_db, test_session.name)
    
    assert session is not None
    assert session.id == test_session.id
    assert session.name == test_session.name


def test_load_session_nonexistent(test_db: DBSession):
    """Test loading a non-existent session."""
    geoparserv2 = GeoparserV2.__new__(GeoparserV2)  # Create instance without calling __init__
    
    # Call load_session directly with a non-existent session name
    session = geoparserv2.load_session(test_db, "non-existent-session")
    
    assert session is None


def test_create_session(test_db: DBSession):
    """Test creating a new session."""
    geoparserv2 = GeoparserV2.__new__(GeoparserV2)  # Create instance without calling __init__
    
    # Call create_session directly
    session_name = "new-test-session"
    session = geoparserv2.create_session(test_db, session_name)
    
    assert session is not None
    assert session.name == session_name
    
    # Verify it was saved to the database
    db_session = SessionRepository.get_by_name(test_db, session_name)
    assert db_session is not None
    assert db_session.name == session_name


def test_init_with_existing_session(geoparserv2_with_existing_session, test_session):
    """Test initializing GeoparserV2 with an existing session."""
    geoparserv2 = geoparserv2_with_existing_session
    
    assert geoparserv2.session is not None
    assert geoparserv2.session.id == test_session.id
    assert geoparserv2.session.name == test_session.name


def test_init_with_new_session(geoparserv2_with_new_session, test_db):
    """Test initializing GeoparserV2 with a new session name."""
    geoparserv2 = geoparserv2_with_new_session
    
    assert geoparserv2.session is not None
    assert geoparserv2.session.name == "new-test-session"
    
    # Verify it was saved to the database
    db_session = SessionRepository.get_by_name(test_db, "new-test-session")
    assert db_session is not None
    assert db_session.name == "new-test-session"


def test_load_or_create_session_existing(mock_get_db, test_db, test_session):
    """Test _load_or_create_session with an existing session."""
    geoparserv2 = GeoparserV2.__new__(GeoparserV2)  # Create instance without calling __init__
    
    # Mock the load_session and create_session methods
    with patch.object(geoparserv2, 'load_session', return_value=test_session) as mock_load:
        with patch.object(geoparserv2, 'create_session') as mock_create:
            session = geoparserv2._load_or_create_session(test_session.name)
            
            # Verify load_session was called with the correct arguments
            mock_load.assert_called_once_with(test_db, test_session.name)
            
            # Verify create_session was not called
            mock_create.assert_not_called()
            
            # Verify the correct session was returned
            assert session == test_session


def test_load_or_create_session_new(mock_get_db, test_db):
    """Test _load_or_create_session with a new session."""
    geoparserv2 = GeoparserV2.__new__(GeoparserV2)  # Create instance without calling __init__
    
    new_session = Session(name="new-session", id=uuid.uuid4())
    
    # Mock the load_session and create_session methods
    with patch.object(geoparserv2, 'load_session', return_value=None) as mock_load:
        with patch.object(geoparserv2, 'create_session', return_value=new_session) as mock_create:
            with patch('geoparser.geoparserv2.geoparserv2.logging.info') as mock_log:
                session = geoparserv2._load_or_create_session("new-session")
                
                # Verify load_session was called with the correct arguments
                mock_load.assert_called_once_with(test_db, "new-session")
                
                # Verify create_session was called with the correct arguments
                mock_create.assert_called_once_with(test_db, "new-session")
                
                # Verify logging was called
                mock_log.assert_called_once()
                assert "No session found with name 'new-session'" in mock_log.call_args[0][0]
                
                # Verify the correct session was returned
                assert session == new_session


def test_add_documents_single(mock_get_db, test_db, geoparserv2_with_existing_session):
    """Test adding a single document."""
    geoparserv2 = geoparserv2_with_existing_session
    
    # Add a single document
    document_ids = geoparserv2.add_documents("This is a test document.")
    
    # Verify the document was created
    assert len(document_ids) == 1
    
    # Verify it was saved to the database
    document = test_db.get(Document, document_ids[0])
    assert document is not None
    assert document.text == "This is a test document."
    assert document.session_id == geoparserv2.session.id


def test_add_documents_multiple(mock_get_db, test_db, geoparserv2_with_existing_session):
    """Test adding multiple documents."""
    geoparserv2 = geoparserv2_with_existing_session
    
    # Add multiple documents
    texts = [
        "This is the first test document.",
        "This is the second test document.",
        "This is the third test document."
    ]
    document_ids = geoparserv2.add_documents(texts)
    
    # Verify the documents were created
    assert len(document_ids) == 3
    
    # Verify they were saved to the database
    for i, doc_id in enumerate(document_ids):
        document = test_db.get(Document, doc_id)
        assert document is not None
        assert document.text == texts[i]
        assert document.session_id == geoparserv2.session.id
    
    # Verify we can retrieve all documents for the session
    documents = DocumentRepository.get_by_session(test_db, geoparserv2.session.id)
    assert len(documents) == 3