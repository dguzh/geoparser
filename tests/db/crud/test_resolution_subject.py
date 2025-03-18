import uuid

from sqlmodel import Session as DBSession

from geoparser.db.crud import ResolutionSubjectRepository, ToponymRepository
from geoparser.db.models import (
    ResolutionSubject,
    ResolutionSubjectCreate,
    ResolutionModule,
    ResolutionModuleCreate,
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
        toponym_id=test_resolution_subject.toponym_id
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
    subject_update = ResolutionSubjectUpdate(id=test_resolution_subject.id, module_id=module.id)
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
    deleted_subject = ResolutionSubjectRepository.delete(test_db, id=test_resolution_subject.id)

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