import uuid

from sqlmodel import Session

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
    test_db: Session,
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


def test_get(test_db: Session, test_resolution_subject: ResolutionSubject):
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
    test_db: Session,
    test_toponym: Toponym,
    test_resolution_subject: ResolutionSubject,
    test_resolution_module: ResolutionModule,
):
    """Test getting resolution subjects by toponym ID."""
    # Create another resolution module
    config = {"module_name": "another-resolution-module", "gazetteer": "test-gazetteer"}

    module_create = ResolutionModuleCreate(config=config)
    module = ResolutionModule(config=module_create.config)
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
    test_db: Session,
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


def test_get_all(test_db: Session, test_resolution_subject: ResolutionSubject):
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


def test_update(test_db: Session, test_resolution_subject: ResolutionSubject):
    """Test updating a resolution subject."""
    # Create a new module
    config = {"module_name": "updated-module", "gazetteer": "updated-gazetteer"}

    module_create = ResolutionModuleCreate(config=config)
    module = ResolutionModule(config=module_create.config)
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


def test_delete(test_db: Session, test_resolution_subject: ResolutionSubject):
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
    test_db: Session,
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


def test_get_unprocessed_toponyms(
    test_db: Session,
    test_document: Document,
    test_toponym: Toponym,
    test_resolution_module: ResolutionModule,
    test_resolution_subject: ResolutionSubject,
):
    """Test getting unprocessed toponyms from a project."""
    # Create another document in the same project
    doc_create = DocumentCreate(
        text="Another test document with Berlin and Paris.",
        project_id=test_document.project_id,
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
    config = {
        "module_name": "different-resolution-module",
        "gazetteer": "different-gazetteer",
    }

    new_module_create = ResolutionModuleCreate(config=config)
    new_module = ResolutionModule(config=new_module_create.config)
    test_db.add(new_module)
    test_db.commit()
    test_db.refresh(new_module)

    subject_create = ResolutionSubjectCreate(
        module_id=new_module.id, toponym_id=new_toponym1.id
    )
    ResolutionSubjectRepository.create(test_db, subject_create)

    # Get unprocessed toponyms for test_resolution_module
    unprocessed_toponyms = ResolutionSubjectRepository.get_unprocessed_toponyms(
        test_db, test_document.project_id, test_resolution_module.id
    )

    # Should return new_toponym1 and new_toponym2 (not processed by test_resolution_module)
    assert len(unprocessed_toponyms) == 2
    toponym_ids = [toponym.id for toponym in unprocessed_toponyms]
    assert new_toponym1.id in toponym_ids
    assert new_toponym2.id in toponym_ids
    assert (
        test_toponym.id not in toponym_ids
    )  # Already processed by test_resolution_module

    # Get unprocessed toponyms for new_module
    unprocessed_toponyms = ResolutionSubjectRepository.get_unprocessed_toponyms(
        test_db, test_document.project_id, new_module.id
    )

    # Should return test_toponym and new_toponym2 (not processed by new_module)
    assert len(unprocessed_toponyms) == 2
    toponym_ids = [toponym.id for toponym in unprocessed_toponyms]
    assert test_toponym.id in toponym_ids
    assert new_toponym2.id in toponym_ids
    assert new_toponym1.id not in toponym_ids  # Already processed by new_module

    # Test with non-existent project ID
    unprocessed_toponyms = ResolutionSubjectRepository.get_unprocessed_toponyms(
        test_db, uuid.uuid4(), test_resolution_module.id
    )
    assert len(unprocessed_toponyms) == 0
