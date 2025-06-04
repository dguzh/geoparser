import uuid

from sqlmodel import Session

from geoparser.db.crud import RecognitionObjectRepository, ReferenceRepository
from geoparser.db.models import (
    RecognitionModule,
    RecognitionModuleCreate,
    RecognitionObject,
    RecognitionObjectCreate,
    RecognitionObjectUpdate,
    Reference,
    ReferenceCreate,
)


def test_create(
    test_db: Session,
    test_reference: Reference,
    test_recognition_module: RecognitionModule,
):
    """Test creating a recognition object."""
    # Create a recognition object using the create model with all required fields
    recognition_create = RecognitionObjectCreate(
        module_id=test_recognition_module.id, reference_id=test_reference.id
    )

    # Create the recognition object
    created_recognition = RecognitionObjectRepository.create(
        test_db, recognition_create
    )

    assert created_recognition.id is not None
    assert created_recognition.reference_id == test_reference.id
    assert created_recognition.module_id == test_recognition_module.id

    # Verify it was saved to the database
    db_recognition = test_db.get(RecognitionObject, created_recognition.id)
    assert db_recognition is not None
    assert db_recognition.reference_id == test_reference.id
    assert db_recognition.module_id == test_recognition_module.id


def test_get(test_db: Session, test_recognition_object: RecognitionObject):
    """Test getting a recognition object by ID."""
    # Test with valid ID
    recognition = RecognitionObjectRepository.get(test_db, test_recognition_object.id)
    assert recognition is not None
    assert recognition.id == test_recognition_object.id
    assert recognition.reference_id == test_recognition_object.reference_id
    assert recognition.module_id == test_recognition_object.module_id

    # Test with invalid ID
    invalid_id = uuid.uuid4()
    recognition = RecognitionObjectRepository.get(test_db, invalid_id)
    assert recognition is None


def test_get_by_reference(
    test_db: Session,
    test_reference: Reference,
    test_recognition_object: RecognitionObject,
    test_recognition_module: RecognitionModule,
):
    """Test getting recognition objects by reference ID."""
    # Create another recognition module
    config = {"model": "another-model"}
    module_create = RecognitionModuleCreate(
        name="another-recognition-module", config=config
    )
    module = RecognitionModule(name=module_create.name, config=module_create.config)
    test_db.add(module)
    test_db.commit()
    test_db.refresh(module)

    # Create another recognition object for the same reference
    recognition_create = RecognitionObjectCreate(
        module_id=module.id, reference_id=test_reference.id
    )

    # Create the recognition object
    RecognitionObjectRepository.create(test_db, recognition_create)

    # Get recognition objects by reference
    recognitions = RecognitionObjectRepository.get_by_reference(
        test_db, test_reference.id
    )
    assert len(recognitions) == 2
    assert any(r.module_id == test_recognition_module.id for r in recognitions)
    assert any(r.module_id == module.id for r in recognitions)

    # Test with invalid reference ID
    invalid_id = uuid.uuid4()
    recognitions = RecognitionObjectRepository.get_by_reference(test_db, invalid_id)
    assert len(recognitions) == 0


def test_get_by_module(
    test_db: Session,
    test_recognition_object: RecognitionObject,
    test_recognition_module: RecognitionModule,
):
    """Test getting recognition objects by module ID."""
    # Create another reference
    reference_create = ReferenceCreate(
        start=10, end=14, document_id=test_recognition_object.reference.document_id
    )

    # Create the reference
    reference = ReferenceRepository.create(test_db, reference_create)

    # Create another recognition object for the same module
    recognition_create = RecognitionObjectCreate(
        module_id=test_recognition_module.id, reference_id=reference.id
    )

    # Create the recognition object
    RecognitionObjectRepository.create(test_db, recognition_create)

    # Get recognition objects by module
    recognitions = RecognitionObjectRepository.get_by_module(
        test_db, test_recognition_module.id
    )
    assert len(recognitions) == 2

    # Test with invalid module ID
    invalid_id = uuid.uuid4()
    recognitions = RecognitionObjectRepository.get_by_module(test_db, invalid_id)
    assert len(recognitions) == 0


def test_get_all(test_db: Session, test_recognition_object: RecognitionObject):
    """Test getting all recognition objects."""
    # Create another recognition object
    recognition_create = RecognitionObjectCreate(
        module_id=test_recognition_object.module_id,
        reference_id=test_recognition_object.reference_id,
    )

    # Create the recognition object
    RecognitionObjectRepository.create(test_db, recognition_create)

    # Get all recognition objects
    recognitions = RecognitionObjectRepository.get_all(test_db)
    assert len(recognitions) >= 2


def test_update(test_db: Session, test_recognition_object: RecognitionObject):
    """Test updating a recognition object."""
    # Create a new module
    config = {"model": "updated-model"}
    module_create = RecognitionModuleCreate(name="updated-module", config=config)
    module = RecognitionModule(name=module_create.name, config=module_create.config)
    test_db.add(module)
    test_db.commit()
    test_db.refresh(module)

    # Update the recognition object
    recognition_update = RecognitionObjectUpdate(
        id=test_recognition_object.id, module_id=module.id
    )
    updated_recognition = RecognitionObjectRepository.update(
        test_db, db_obj=test_recognition_object, obj_in=recognition_update
    )

    assert updated_recognition.id == test_recognition_object.id
    assert updated_recognition.module_id == module.id

    # Verify it was updated in the database
    db_recognition = test_db.get(RecognitionObject, test_recognition_object.id)
    assert db_recognition is not None
    assert db_recognition.module_id == module.id


def test_delete(test_db: Session, test_recognition_object: RecognitionObject):
    """Test deleting a recognition object."""
    # Delete the recognition object
    deleted_recognition = RecognitionObjectRepository.delete(
        test_db, id=test_recognition_object.id
    )

    assert deleted_recognition is not None
    assert deleted_recognition.id == test_recognition_object.id

    # Verify it was deleted from the database
    db_recognition = test_db.get(RecognitionObject, test_recognition_object.id)
    assert db_recognition is None
