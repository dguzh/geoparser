import uuid

from sqlmodel import Session

from geoparser.db.crud import DocumentRepository, RecognitionRepository
from geoparser.db.models import (
    Document,
    DocumentCreate,
    Recognition,
    RecognitionCreate,
    RecognitionUpdate,
    Recognizer,
    RecognizerCreate,
)


def test_create(
    test_db: Session,
    test_document: Document,
    test_recognizer: Recognizer,
):
    """Test creating a recognition."""
    # Create a recognition using the create model with all required fields
    recognition_create = RecognitionCreate(
        recognizer_id=test_recognizer.id, document_id=test_document.id
    )

    # Create the recognition
    created_recognition = RecognitionRepository.create(test_db, recognition_create)

    assert created_recognition.id is not None
    assert created_recognition.document_id == test_document.id
    assert created_recognition.recognizer_id == test_recognizer.id

    # Verify it was saved to the database
    db_recognition = test_db.get(Recognition, created_recognition.id)
    assert db_recognition is not None
    assert db_recognition.document_id == test_document.id
    assert db_recognition.recognizer_id == test_recognizer.id


def test_get(test_db: Session, test_recognition: Recognition):
    """Test getting a recognition by ID."""
    # Test with valid ID
    recognition = RecognitionRepository.get(test_db, test_recognition.id)
    assert recognition is not None
    assert recognition.id == test_recognition.id
    assert recognition.document_id == test_recognition.document_id
    assert recognition.recognizer_id == test_recognition.recognizer_id

    # Test with invalid ID
    invalid_id = uuid.uuid4()
    recognition = RecognitionRepository.get(test_db, invalid_id)
    assert recognition is None


def test_get_by_document(
    test_db: Session,
    test_document: Document,
    test_recognition: Recognition,
    test_recognizer: Recognizer,
):
    """Test getting recognitions by document ID."""
    # Create another recognition module
    config = {"model": "another-model"}
    module_create = RecognizerCreate(name="another-recognition-module", config=config)
    module = Recognizer(name=module_create.name, config=module_create.config)
    test_db.add(module)
    test_db.commit()
    test_db.refresh(module)

    # Create another recognition for the same document
    recognition_create = RecognitionCreate(
        recognizer_id=module.id, document_id=test_document.id
    )

    # Create the recognition
    RecognitionRepository.create(test_db, recognition_create)

    # Get recognitions by document
    recognitions = RecognitionRepository.get_by_document(test_db, test_document.id)
    assert len(recognitions) == 2
    assert any(r.recognizer_id == test_recognizer.id for r in recognitions)
    assert any(r.recognizer_id == module.id for r in recognitions)

    # Test with invalid document ID
    invalid_id = uuid.uuid4()
    recognitions = RecognitionRepository.get_by_document(test_db, invalid_id)
    assert len(recognitions) == 0


def test_get_by_recognizer(
    test_db: Session,
    test_recognition: Recognition,
    test_recognizer: Recognizer,
):
    """Test getting recognitions by recognizer ID."""
    # Create another document
    doc_create = DocumentCreate(
        text="Another test document.",
        project_id=test_recognition.document.project_id,
    )

    # Create the document
    document = DocumentRepository.create(test_db, doc_create)

    # Create another recognition for the same recognizer
    recognition_create = RecognitionCreate(
        recognizer_id=test_recognizer.id, document_id=document.id
    )

    # Create the recognition
    RecognitionRepository.create(test_db, recognition_create)

    # Get recognitions by recognizer
    recognitions = RecognitionRepository.get_by_recognizer(test_db, test_recognizer.id)
    assert len(recognitions) == 2

    # Test with invalid recognizer ID
    invalid_id = uuid.uuid4()
    recognitions = RecognitionRepository.get_by_recognizer(test_db, invalid_id)
    assert len(recognitions) == 0


def test_get_all(test_db: Session, test_recognition: Recognition):
    """Test getting all recognitions."""
    # Create another recognition
    recognition_create = RecognitionCreate(
        recognizer_id=test_recognition.recognizer_id,
        document_id=test_recognition.document_id,
    )

    # Create the recognition
    RecognitionRepository.create(test_db, recognition_create)

    # Get all recognitions
    recognitions = RecognitionRepository.get_all(test_db)
    assert len(recognitions) >= 2


def test_update(test_db: Session, test_recognition: Recognition):
    """Test updating a recognition."""
    # Create a new module
    config = {"model": "updated-model"}
    module_create = RecognizerCreate(name="updated-module", config=config)
    module = Recognizer(name=module_create.name, config=module_create.config)
    test_db.add(module)
    test_db.commit()
    test_db.refresh(module)

    # Update the recognition
    recognition_update = RecognitionUpdate(
        id=test_recognition.id, recognizer_id=module.id
    )
    updated_recognition = RecognitionRepository.update(
        test_db, db_obj=test_recognition, obj_in=recognition_update
    )

    assert updated_recognition.id == test_recognition.id
    assert updated_recognition.recognizer_id == module.id

    # Verify it was updated in the database
    db_recognition = test_db.get(Recognition, test_recognition.id)
    assert db_recognition is not None
    assert db_recognition.recognizer_id == module.id


def test_delete(test_db: Session, test_recognition: Recognition):
    """Test deleting a recognition."""
    # Delete the recognition
    deleted_recognition = RecognitionRepository.delete(test_db, id=test_recognition.id)

    assert deleted_recognition is not None
    assert deleted_recognition.id == test_recognition.id

    # Verify it was deleted from the database
    db_recognition = test_db.get(Recognition, test_recognition.id)
    assert db_recognition is None


def test_get_by_document_and_recognizer(
    test_db: Session,
    test_document: Document,
    test_recognizer: Recognizer,
    test_recognition: Recognition,
):
    """Test getting a recognition by document and recognizer."""
    # Test with valid IDs
    recognition = RecognitionRepository.get_by_document_and_recognizer(
        test_db, test_document.id, test_recognizer.id
    )
    assert recognition is not None
    assert recognition.document_id == test_document.id
    assert recognition.recognizer_id == test_recognizer.id

    # Test with invalid IDs
    invalid_id = uuid.uuid4()
    recognition = RecognitionRepository.get_by_document_and_recognizer(
        test_db, invalid_id, test_recognizer.id
    )
    assert recognition is None

    recognition = RecognitionRepository.get_by_document_and_recognizer(
        test_db, test_document.id, invalid_id
    )
    assert recognition is None


def test_get_unprocessed_documents(
    test_db: Session,
    test_document: Document,
    test_recognizer: Recognizer,
    test_recognition: Recognition,
):
    """Test getting unprocessed documents from a project."""
    # Create another document in the same project
    doc_create = DocumentCreate(
        text="Another test document.", project_id=test_document.project_id
    )
    another_document = DocumentRepository.create(test_db, doc_create)

    # Create a third document in the same project
    doc_create = DocumentCreate(
        text="Yet another test document.", project_id=test_document.project_id
    )
    third_document = DocumentRepository.create(test_db, doc_create)

    # Process the third document with a different module
    config = {"model": "different-model"}
    new_module_create = RecognizerCreate(
        name="different-recognition-module", config=config
    )
    new_module = Recognizer(
        name=new_module_create.name, config=new_module_create.config
    )
    test_db.add(new_module)
    test_db.commit()
    test_db.refresh(new_module)

    recognition_create = RecognitionCreate(
        recognizer_id=new_module.id, document_id=third_document.id
    )
    RecognitionRepository.create(test_db, recognition_create)

    # Get unprocessed documents for test_recognizer
    unprocessed_docs = RecognitionRepository.get_unprocessed_documents(
        test_db, test_document.project_id, test_recognizer.id
    )

    # Should return another_document and third_document (not processed by test_recognizer)
    assert len(unprocessed_docs) == 2
    doc_ids = [doc.id for doc in unprocessed_docs]
    assert another_document.id in doc_ids
    assert third_document.id in doc_ids
    assert test_document.id not in doc_ids  # Already processed by test_recognizer

    # Get unprocessed documents for new_module
    unprocessed_docs = RecognitionRepository.get_unprocessed_documents(
        test_db, test_document.project_id, new_module.id
    )

    # Should return test_document and another_document (not processed by new_module)
    assert len(unprocessed_docs) == 2
    doc_ids = [doc.id for doc in unprocessed_docs]
    assert test_document.id in doc_ids
    assert another_document.id in doc_ids
    assert third_document.id not in doc_ids  # Already processed by new_module

    # Test with non-existent project ID
    unprocessed_docs = RecognitionRepository.get_unprocessed_documents(
        test_db, uuid.uuid4(), test_recognizer.id
    )
    assert len(unprocessed_docs) == 0
