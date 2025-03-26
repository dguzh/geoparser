import uuid

from sqlmodel import Session as DBSession

from geoparser.db.crud import DocumentRepository
from geoparser.db.models import Document, DocumentCreate, DocumentUpdate, Project


def test_create(test_db: DBSession, test_project: Project):
    """Test creating a document."""
    # Create a document using the create model with all required fields
    document_create = DocumentCreate(
        text="This is a test document.", project_id=test_project.id
    )

    # Create the document
    created_document = DocumentRepository.create(test_db, document_create)

    assert created_document.id is not None
    assert created_document.text == "This is a test document."
    assert created_document.project_id == test_project.id

    # Verify it was saved to the database
    db_document = test_db.get(Document, created_document.id)
    assert db_document is not None
    assert db_document.text == "This is a test document."
    assert db_document.project_id == test_project.id


def test_get(test_db: DBSession, test_document: Document):
    """Test getting a document by ID."""
    # Test with valid ID
    document = DocumentRepository.get(test_db, test_document.id)
    assert document is not None
    assert document.id == test_document.id
    assert document.text == test_document.text

    # Test with invalid ID
    invalid_id = uuid.uuid4()
    document = DocumentRepository.get(test_db, invalid_id)
    assert document is None


def test_get_by_project(
    test_db: DBSession, test_project: Project, test_document: Document
):
    """Test getting documents by project ID."""
    # Create another document in the same project
    document_create = DocumentCreate(
        text="Another test document.", project_id=test_project.id
    )

    # Create the document
    DocumentRepository.create(test_db, document_create)

    # Get documents by project
    documents = DocumentRepository.get_by_project(test_db, test_project.id)
    assert len(documents) == 2
    assert any(d.text == "This is a test document with Berlin." for d in documents)
    assert any(d.text == "Another test document." for d in documents)

    # Test with invalid project ID
    invalid_id = uuid.uuid4()
    documents = DocumentRepository.get_by_project(test_db, invalid_id)
    assert len(documents) == 0


def test_get_all(test_db: DBSession, test_document: Document):
    """Test getting all documents."""
    # Create another document
    document_create = DocumentCreate(
        text="Another test document.", project_id=test_document.project_id
    )

    # Create the document
    DocumentRepository.create(test_db, document_create)

    # Get all documents
    documents = DocumentRepository.get_all(test_db)
    assert len(documents) == 2
    assert any(d.text == "This is a test document with Berlin." for d in documents)
    assert any(d.text == "Another test document." for d in documents)


def test_update(test_db: DBSession, test_document: Document):
    """Test updating a document."""
    # Update the document
    document_update = DocumentUpdate(id=test_document.id, text="Updated document text.")
    updated_document = DocumentRepository.update(
        test_db, db_obj=test_document, obj_in=document_update
    )

    assert updated_document.id == test_document.id
    assert updated_document.text == "Updated document text."

    # Verify it was updated in the database
    db_document = test_db.get(Document, test_document.id)
    assert db_document is not None
    assert db_document.text == "Updated document text."


def test_delete(test_db: DBSession, test_document: Document):
    """Test deleting a document."""
    # Delete the document
    deleted_document = DocumentRepository.delete(test_db, id=test_document.id)

    assert deleted_document is not None
    assert deleted_document.id == test_document.id

    # Verify it was deleted from the database
    db_document = test_db.get(Document, test_document.id)
    assert db_document is None
