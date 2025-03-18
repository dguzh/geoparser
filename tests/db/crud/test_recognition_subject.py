import uuid

from sqlmodel import Session as DBSession

from geoparser.db.crud import DocumentRepository, RecognitionSubjectRepository
from geoparser.db.models import (
    Document,
    DocumentCreate,
    RecognitionModule,
    RecognitionModuleCreate,
    RecognitionSubject,
    RecognitionSubjectCreate,
    RecognitionSubjectUpdate,
)


def test_create(
    test_db: DBSession,
    test_document: Document,
    test_recognition_module: RecognitionModule,
):
    """Test creating a recognition subject."""
    # Create a recognition subject using the create model with all required fields
    subject_create = RecognitionSubjectCreate(
        module_id=test_recognition_module.id, document_id=test_document.id
    )

    # Create the recognition subject
    created_subject = RecognitionSubjectRepository.create(test_db, subject_create)

    assert created_subject.id is not None
    assert created_subject.document_id == test_document.id
    assert created_subject.module_id == test_recognition_module.id

    # Verify it was saved to the database
    db_subject = test_db.get(RecognitionSubject, created_subject.id)
    assert db_subject is not None
    assert db_subject.document_id == test_document.id
    assert db_subject.module_id == test_recognition_module.id


def test_get(test_db: DBSession, test_recognition_subject: RecognitionSubject):
    """Test getting a recognition subject by ID."""
    # Test with valid ID
    subject = RecognitionSubjectRepository.get(test_db, test_recognition_subject.id)
    assert subject is not None
    assert subject.id == test_recognition_subject.id
    assert subject.document_id == test_recognition_subject.document_id
    assert subject.module_id == test_recognition_subject.module_id

    # Test with invalid ID
    invalid_id = uuid.uuid4()
    subject = RecognitionSubjectRepository.get(test_db, invalid_id)
    assert subject is None


def test_get_by_document(
    test_db: DBSession,
    test_document: Document,
    test_recognition_subject: RecognitionSubject,
    test_recognition_module: RecognitionModule,
):
    """Test getting recognition subjects by document ID."""
    # Create another recognition module
    module_create = RecognitionModuleCreate(name="another-recognition-module")
    module = RecognitionModule(name=module_create.name)
    test_db.add(module)
    test_db.commit()
    test_db.refresh(module)

    # Create another recognition subject for the same document
    subject_create = RecognitionSubjectCreate(
        module_id=module.id, document_id=test_document.id
    )

    # Create the recognition subject
    RecognitionSubjectRepository.create(test_db, subject_create)

    # Get recognition subjects by document
    subjects = RecognitionSubjectRepository.get_by_document(test_db, test_document.id)
    assert len(subjects) == 2
    assert any(s.module_id == test_recognition_module.id for s in subjects)
    assert any(s.module_id == module.id for s in subjects)

    # Test with invalid document ID
    invalid_id = uuid.uuid4()
    subjects = RecognitionSubjectRepository.get_by_document(test_db, invalid_id)
    assert len(subjects) == 0


def test_get_by_module(
    test_db: DBSession,
    test_recognition_subject: RecognitionSubject,
    test_recognition_module: RecognitionModule,
):
    """Test getting recognition subjects by module ID."""
    # Create another document
    doc_create = DocumentCreate(
        text="Another test document.",
        session_id=test_recognition_subject.document.session_id,
    )

    # Create the document
    document = DocumentRepository.create(test_db, doc_create)

    # Create another recognition subject for the same module
    subject_create = RecognitionSubjectCreate(
        module_id=test_recognition_module.id, document_id=document.id
    )

    # Create the recognition subject
    RecognitionSubjectRepository.create(test_db, subject_create)

    # Get recognition subjects by module
    subjects = RecognitionSubjectRepository.get_by_module(
        test_db, test_recognition_module.id
    )
    assert len(subjects) == 2

    # Test with invalid module ID
    invalid_id = uuid.uuid4()
    subjects = RecognitionSubjectRepository.get_by_module(test_db, invalid_id)
    assert len(subjects) == 0


def test_get_all(test_db: DBSession, test_recognition_subject: RecognitionSubject):
    """Test getting all recognition subjects."""
    # Create another recognition subject
    subject_create = RecognitionSubjectCreate(
        module_id=test_recognition_subject.module_id,
        document_id=test_recognition_subject.document_id,
    )

    # Create the recognition subject
    RecognitionSubjectRepository.create(test_db, subject_create)

    # Get all recognition subjects
    subjects = RecognitionSubjectRepository.get_all(test_db)
    assert len(subjects) >= 2


def test_update(test_db: DBSession, test_recognition_subject: RecognitionSubject):
    """Test updating a recognition subject."""
    # Create a new module
    module_create = RecognitionModuleCreate(name="updated-module")
    module = RecognitionModule(name=module_create.name)
    test_db.add(module)
    test_db.commit()
    test_db.refresh(module)

    # Update the recognition subject
    subject_update = RecognitionSubjectUpdate(
        id=test_recognition_subject.id, module_id=module.id
    )
    updated_subject = RecognitionSubjectRepository.update(
        test_db, db_obj=test_recognition_subject, obj_in=subject_update
    )

    assert updated_subject.id == test_recognition_subject.id
    assert updated_subject.module_id == module.id

    # Verify it was updated in the database
    db_subject = test_db.get(RecognitionSubject, test_recognition_subject.id)
    assert db_subject is not None
    assert db_subject.module_id == module.id


def test_delete(test_db: DBSession, test_recognition_subject: RecognitionSubject):
    """Test deleting a recognition subject."""
    # Delete the recognition subject
    deleted_subject = RecognitionSubjectRepository.delete(
        test_db, id=test_recognition_subject.id
    )

    assert deleted_subject is not None
    assert deleted_subject.id == test_recognition_subject.id

    # Verify it was deleted from the database
    db_subject = test_db.get(RecognitionSubject, test_recognition_subject.id)
    assert db_subject is None


def test_get_by_document_and_module(
    test_db: DBSession,
    test_document: Document,
    test_recognition_module: RecognitionModule,
    test_recognition_subject: RecognitionSubject,
):
    """Test getting a recognition subject by document and module."""
    # Test with valid IDs
    subject = RecognitionSubjectRepository.get_by_document_and_module(
        test_db, test_document.id, test_recognition_module.id
    )
    assert subject is not None
    assert subject.document_id == test_document.id
    assert subject.module_id == test_recognition_module.id

    # Test with invalid IDs
    invalid_id = uuid.uuid4()
    subject = RecognitionSubjectRepository.get_by_document_and_module(
        test_db, invalid_id, test_recognition_module.id
    )
    assert subject is None

    subject = RecognitionSubjectRepository.get_by_document_and_module(
        test_db, test_document.id, invalid_id
    )
    assert subject is None


def test_get_unprocessed_documents(
    test_db: DBSession,
    test_document: Document,
    test_recognition_module: RecognitionModule,
    test_recognition_subject: RecognitionSubject,
):
    """Test getting unprocessed documents from a session."""
    # Create another document in the same session
    doc_create = DocumentCreate(
        text="Another test document.", session_id=test_document.session_id
    )
    another_document = DocumentRepository.create(test_db, doc_create)

    # Create a third document in the same session
    doc_create = DocumentCreate(
        text="Yet another test document.", session_id=test_document.session_id
    )
    third_document = DocumentRepository.create(test_db, doc_create)

    # Process the third document with a different module
    new_module_create = RecognitionModuleCreate(name="different-recognition-module")
    new_module = RecognitionModule(name=new_module_create.name)
    test_db.add(new_module)
    test_db.commit()
    test_db.refresh(new_module)

    subject_create = RecognitionSubjectCreate(
        module_id=new_module.id, document_id=third_document.id
    )
    RecognitionSubjectRepository.create(test_db, subject_create)

    # Get unprocessed documents for test_recognition_module
    unprocessed_docs = RecognitionSubjectRepository.get_unprocessed_documents(
        test_db, test_document.session_id, test_recognition_module.id
    )

    # Should return another_document and third_document (not processed by test_recognition_module)
    assert len(unprocessed_docs) == 2
    doc_ids = [doc.id for doc in unprocessed_docs]
    assert another_document.id in doc_ids
    assert third_document.id in doc_ids
    assert (
        test_document.id not in doc_ids
    )  # Already processed by test_recognition_module

    # Get unprocessed documents for new_module
    unprocessed_docs = RecognitionSubjectRepository.get_unprocessed_documents(
        test_db, test_document.session_id, new_module.id
    )

    # Should return test_document and another_document (not processed by new_module)
    assert len(unprocessed_docs) == 2
    doc_ids = [doc.id for doc in unprocessed_docs]
    assert test_document.id in doc_ids
    assert another_document.id in doc_ids
    assert third_document.id not in doc_ids  # Already processed by new_module

    # Test with non-existent session ID
    unprocessed_docs = RecognitionSubjectRepository.get_unprocessed_documents(
        test_db, uuid.uuid4(), test_recognition_module.id
    )
    assert len(unprocessed_docs) == 0


def test_create_many(
    test_db: DBSession,
    test_recognition_module: RecognitionModule,
    test_document: Document,
):
    """Test creating multiple recognition subject records at once."""
    # Create a few documents
    session_id = test_document.session_id

    doc_create1 = DocumentCreate(text="First batch document.", session_id=session_id)
    doc1 = DocumentRepository.create(test_db, doc_create1)

    doc_create2 = DocumentCreate(text="Second batch document.", session_id=session_id)
    doc2 = DocumentRepository.create(test_db, doc_create2)

    doc_create3 = DocumentCreate(text="Third batch document.", session_id=session_id)
    doc3 = DocumentRepository.create(test_db, doc_create3)

    # Create subject records for all documents in one operation
    document_ids = [doc1.id, doc2.id, doc3.id]
    created_subjects = RecognitionSubjectRepository.create_many(
        test_db, document_ids, test_recognition_module.id
    )

    # Check that all subjects were created
    assert len(created_subjects) == 3

    # Verify they were saved to the database
    for doc_id in document_ids:
        subject = RecognitionSubjectRepository.get_by_document_and_module(
            test_db, doc_id, test_recognition_module.id
        )
        assert subject is not None
        assert subject.document_id == doc_id
        assert subject.module_id == test_recognition_module.id
