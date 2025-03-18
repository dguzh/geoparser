import uuid

from sqlmodel import Session as DBSession

from geoparser.db.crud import RecognitionSubjectRepository, DocumentRepository
from geoparser.db.models import (
    RecognitionSubject,
    RecognitionSubjectCreate,
    RecognitionModule,
    RecognitionModuleCreate,
    RecognitionSubjectUpdate,
    Document,
    DocumentCreate,
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
        session_id=test_recognition_subject.document.session_id
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
        document_id=test_recognition_subject.document_id
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
    subject_update = RecognitionSubjectUpdate(id=test_recognition_subject.id, module_id=module.id)
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
    deleted_subject = RecognitionSubjectRepository.delete(test_db, id=test_recognition_subject.id)

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