import uuid

from sqlmodel import Session as DBSession

from geoparser.db.crud import (
    DocumentRepository,
    ResolutionSubjectRepository,
    ToponymRepository,
)
from geoparser.db.models import (
    Document,
    DocumentCreate,
    ResolutionModule,
    ResolutionModuleCreate,
    ResolutionSubject,
    ResolutionSubjectCreate,
    ResolutionSubjectUpdate,
    Toponym,
    ToponymCreate,
)


def test_create(
    test_db: DBSession,
    test_toponym: Toponym,
    test_resolution_module: ResolutionModule,
):
    """Test creating a resolution subject."""
    # Create a resolution subject using the create model with all required fields
    subject_create = ResolutionSubjectCreate(
        module_id=test_resolution_module.id, toponym_id=test_toponym.id
    )

    # Create the resolution subject
    created_subject = ResolutionSubjectRepository.create(test_db, subject_create)

    assert created_subject.id is not None
    assert created_subject.toponym_id == test_toponym.id
    assert created_subject.module_id == test_resolution_module.id

    # Verify it was saved to the database
    db_subject = test_db.get(ResolutionSubject, created_subject.id)
    assert db_subject is not None
    assert db_subject.toponym_id == test_toponym.id
    assert db_subject.module_id == test_resolution_module.id


def test_get(test_db: DBSession, test_resolution_subject: ResolutionSubject):
    """Test getting a resolution subject by ID."""
    # Test with valid ID
    subject = ResolutionSubjectRepository.get(test_db, test_resolution_subject.id)
    assert subject is not None
    assert subject.id == test_resolution_subject.id
    assert subject.toponym_id == test_resolution_subject.toponym_id
    assert subject.module_id == test_resolution_subject.module_id

    # Test with invalid ID
    invalid_id = uuid.uuid4()
    subject = ResolutionSubjectRepository.get(test_db, invalid_id)
    assert subject is None


def test_get_by_toponym(
    test_db: DBSession,
    test_toponym: Toponym,
    test_resolution_subject: ResolutionSubject,
    test_resolution_module: ResolutionModule,
):
    """Test getting resolution subjects by toponym ID."""
    # Create another resolution module
    module_create = ResolutionModuleCreate(name="another-resolution-module")
    module = ResolutionModule(name=module_create.name)
    test_db.add(module)
    test_db.commit()
    test_db.refresh(module)

    # Create another resolution subject for the same toponym
    subject_create = ResolutionSubjectCreate(
        module_id=module.id, toponym_id=test_toponym.id
    )

    # Create the resolution subject
    ResolutionSubjectRepository.create(test_db, subject_create)

    # Get resolution subjects by toponym
    subjects = ResolutionSubjectRepository.get_by_toponym(test_db, test_toponym.id)
    assert len(subjects) == 2
    assert any(s.module_id == test_resolution_module.id for s in subjects)
    assert any(s.module_id == module.id for s in subjects)

    # Test with invalid toponym ID
    invalid_id = uuid.uuid4()
    subjects = ResolutionSubjectRepository.get_by_toponym(test_db, invalid_id)
    assert len(subjects) == 0


def test_get_by_module(
    test_db: DBSession,
    test_resolution_subject: ResolutionSubject,
    test_resolution_module: ResolutionModule,
):
    """Test getting resolution subjects by module ID."""
    # Create another toponym
    toponym_create = ToponymCreate(
        start=40, end=45, document_id=test_resolution_subject.toponym.document_id
    )

    # Create the toponym
    toponym = ToponymRepository.create(test_db, toponym_create)

    # Create another resolution subject for the same module
    subject_create = ResolutionSubjectCreate(
        module_id=test_resolution_module.id, toponym_id=toponym.id
    )

    # Create the resolution subject
    ResolutionSubjectRepository.create(test_db, subject_create)

    # Get resolution subjects by module
    subjects = ResolutionSubjectRepository.get_by_module(
        test_db, test_resolution_module.id
    )
    assert len(subjects) == 2

    # Test with invalid module ID
    invalid_id = uuid.uuid4()
    subjects = ResolutionSubjectRepository.get_by_module(test_db, invalid_id)
    assert len(subjects) == 0


def test_get_all(test_db: DBSession, test_resolution_subject: ResolutionSubject):
    """Test getting all resolution subjects."""
    # Create another resolution subject
    subject_create = ResolutionSubjectCreate(
        module_id=test_resolution_subject.module_id,
        toponym_id=test_resolution_subject.toponym_id,
    )

    # Create the resolution subject
    ResolutionSubjectRepository.create(test_db, subject_create)

    # Get all resolution subjects
    subjects = ResolutionSubjectRepository.get_all(test_db)
    assert len(subjects) >= 2


def test_update(test_db: DBSession, test_resolution_subject: ResolutionSubject):
    """Test updating a resolution subject."""
    # Create a new module
    module_create = ResolutionModuleCreate(name="updated-module")
    module = ResolutionModule(name=module_create.name)
    test_db.add(module)
    test_db.commit()
    test_db.refresh(module)

    # Update the resolution subject
    subject_update = ResolutionSubjectUpdate(
        id=test_resolution_subject.id, module_id=module.id
    )
    updated_subject = ResolutionSubjectRepository.update(
        test_db, db_obj=test_resolution_subject, obj_in=subject_update
    )

    assert updated_subject.id == test_resolution_subject.id
    assert updated_subject.module_id == module.id

    # Verify it was updated in the database
    db_subject = test_db.get(ResolutionSubject, test_resolution_subject.id)
    assert db_subject is not None
    assert db_subject.module_id == module.id


def test_delete(test_db: DBSession, test_resolution_subject: ResolutionSubject):
    """Test deleting a resolution subject."""
    # Delete the resolution subject
    deleted_subject = ResolutionSubjectRepository.delete(
        test_db, id=test_resolution_subject.id
    )

    assert deleted_subject is not None
    assert deleted_subject.id == test_resolution_subject.id

    # Verify it was deleted from the database
    db_subject = test_db.get(ResolutionSubject, test_resolution_subject.id)
    assert db_subject is None


def test_get_by_toponym_and_module(
    test_db: DBSession,
    test_toponym: Toponym,
    test_resolution_module: ResolutionModule,
    test_resolution_subject: ResolutionSubject,
):
    """Test getting a resolution subject by toponym and module."""
    # Test with valid IDs
    subject = ResolutionSubjectRepository.get_by_toponym_and_module(
        test_db, test_toponym.id, test_resolution_module.id
    )
    assert subject is not None
    assert subject.toponym_id == test_toponym.id
    assert subject.module_id == test_resolution_module.id

    # Test with invalid IDs
    invalid_id = uuid.uuid4()
    subject = ResolutionSubjectRepository.get_by_toponym_and_module(
        test_db, invalid_id, test_resolution_module.id
    )
    assert subject is None

    subject = ResolutionSubjectRepository.get_by_toponym_and_module(
        test_db, test_toponym.id, invalid_id
    )
    assert subject is None


def test_get_unprocessed_toponyms_with_documents(
    test_db: DBSession,
    test_document: Document,
    test_toponym: Toponym,
    test_resolution_module: ResolutionModule,
    test_resolution_subject: ResolutionSubject,
):
    """Test getting unprocessed toponyms with their documents from a session."""
    # Create another document in the same session
    doc_create = DocumentCreate(
        text="Another test document with Berlin and Paris.",
        session_id=test_document.session_id,
    )
    another_document = DocumentRepository.create(test_db, doc_create)

    # Create toponyms for the new document
    toponym_create1 = ToponymCreate(
        start=23, end=29, document_id=another_document.id  # "Berlin"
    )
    new_toponym1 = ToponymRepository.create(test_db, toponym_create1)

    toponym_create2 = ToponymCreate(
        start=34, end=39, document_id=another_document.id  # "Paris"
    )
    new_toponym2 = ToponymRepository.create(test_db, toponym_create2)

    # Process one of the new toponyms with a different module
    new_module_create = ResolutionModuleCreate(name="different-resolution-module")
    new_module = ResolutionModule(name=new_module_create.name)
    test_db.add(new_module)
    test_db.commit()
    test_db.refresh(new_module)

    subject_create = ResolutionSubjectCreate(
        module_id=new_module.id, toponym_id=new_toponym1.id
    )
    ResolutionSubjectRepository.create(test_db, subject_create)

    # Get unprocessed toponyms for test_resolution_module
    unprocessed_items = (
        ResolutionSubjectRepository.get_unprocessed_toponyms_with_documents(
            test_db, test_document.session_id, test_resolution_module.id
        )
    )

    # Should return both new toponyms (not processed by test_resolution_module)
    assert len(unprocessed_items) == 2

    # Extract document and toponym IDs for easier checking
    doc_toponym_pairs = [(doc.id, topo.id) for doc, topo in unprocessed_items]
    assert (another_document.id, new_toponym1.id) in doc_toponym_pairs
    assert (another_document.id, new_toponym2.id) in doc_toponym_pairs
    assert (
        test_document.id,
        test_toponym.id,
    ) not in doc_toponym_pairs  # Already processed

    # Get unprocessed toponyms for new_module
    unprocessed_items = (
        ResolutionSubjectRepository.get_unprocessed_toponyms_with_documents(
            test_db, test_document.session_id, new_module.id
        )
    )

    # Should return test_toponym and new_toponym2 (not processed by new_module)
    assert len(unprocessed_items) == 2
    doc_toponym_pairs = [(doc.id, topo.id) for doc, topo in unprocessed_items]
    assert (test_document.id, test_toponym.id) in doc_toponym_pairs
    assert (another_document.id, new_toponym2.id) in doc_toponym_pairs
    assert (
        another_document.id,
        new_toponym1.id,
    ) not in doc_toponym_pairs  # Already processed by new_module

    # Test with non-existent session ID
    unprocessed_items = (
        ResolutionSubjectRepository.get_unprocessed_toponyms_with_documents(
            test_db, uuid.uuid4(), test_resolution_module.id
        )
    )
    assert len(unprocessed_items) == 0


def test_create_many(
    test_db: DBSession,
    test_document: Document,
    test_resolution_module: ResolutionModule,
):
    """Test creating multiple resolution subject records at once."""
    # Create a few toponyms
    toponym_create1 = ToponymCreate(start=10, end=15, document_id=test_document.id)
    toponym1 = ToponymRepository.create(test_db, toponym_create1)

    toponym_create2 = ToponymCreate(start=20, end=25, document_id=test_document.id)
    toponym2 = ToponymRepository.create(test_db, toponym_create2)

    toponym_create3 = ToponymCreate(start=30, end=35, document_id=test_document.id)
    toponym3 = ToponymRepository.create(test_db, toponym_create3)

    # Create subject records for all toponyms in one operation
    toponym_ids = [toponym1.id, toponym2.id, toponym3.id]
    created_subjects = ResolutionSubjectRepository.create_many(
        test_db, toponym_ids, test_resolution_module.id
    )

    # Check that all subjects were created
    assert len(created_subjects) == 3

    # Verify they were saved to the database
    for toponym_id in toponym_ids:
        subject = ResolutionSubjectRepository.get_by_toponym_and_module(
            test_db, toponym_id, test_resolution_module.id
        )
        assert subject is not None
        assert subject.toponym_id == toponym_id
        assert subject.module_id == test_resolution_module.id
