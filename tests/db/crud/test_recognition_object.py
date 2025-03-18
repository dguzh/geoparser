import uuid

from sqlmodel import Session as DBSession

from geoparser.db.crud import RecognitionObjectRepository, ToponymRepository
from geoparser.db.models import (
    RecognitionModule,
    RecognitionModuleCreate,
    RecognitionObject,
    RecognitionObjectCreate,
    RecognitionObjectUpdate,
    Toponym,
    ToponymCreate,
)


def test_create(
    test_db: DBSession,
    test_toponym: Toponym,
    test_recognition_module: RecognitionModule,
):
    """Test creating a recognition object."""
    # Create a recognition object using the create model with all required fields
    recognition_create = RecognitionObjectCreate(
        module_id=test_recognition_module.id, toponym_id=test_toponym.id
    )

    # Create the recognition object
    created_recognition = RecognitionObjectRepository.create(
        test_db, recognition_create
    )

    assert created_recognition.id is not None
    assert created_recognition.toponym_id == test_toponym.id
    assert created_recognition.module_id == test_recognition_module.id

    # Verify it was saved to the database
    db_recognition = test_db.get(RecognitionObject, created_recognition.id)
    assert db_recognition is not None
    assert db_recognition.toponym_id == test_toponym.id
    assert db_recognition.module_id == test_recognition_module.id


def test_get(test_db: DBSession, test_recognition_object: RecognitionObject):
    """Test getting a recognition object by ID."""
    # Test with valid ID
    recognition = RecognitionObjectRepository.get(test_db, test_recognition_object.id)
    assert recognition is not None
    assert recognition.id == test_recognition_object.id
    assert recognition.toponym_id == test_recognition_object.toponym_id
    assert recognition.module_id == test_recognition_object.module_id

    # Test with invalid ID
    invalid_id = uuid.uuid4()
    recognition = RecognitionObjectRepository.get(test_db, invalid_id)
    assert recognition is None


def test_get_by_toponym(
    test_db: DBSession,
    test_toponym: Toponym,
    test_recognition_object: RecognitionObject,
    test_recognition_module: RecognitionModule,
):
    """Test getting recognition objects by toponym ID."""
    # Create another recognition module
    module_create = RecognitionModuleCreate(name="another-recognition-module")
    module = RecognitionModule(name=module_create.name)
    test_db.add(module)
    test_db.commit()
    test_db.refresh(module)

    # Create another recognition object for the same toponym
    recognition_create = RecognitionObjectCreate(
        module_id=module.id, toponym_id=test_toponym.id
    )

    # Create the recognition object
    RecognitionObjectRepository.create(test_db, recognition_create)

    # Get recognition objects by toponym
    recognitions = RecognitionObjectRepository.get_by_toponym(test_db, test_toponym.id)
    assert len(recognitions) == 2
    assert any(r.module_id == test_recognition_module.id for r in recognitions)
    assert any(r.module_id == module.id for r in recognitions)

    # Test with invalid toponym ID
    invalid_id = uuid.uuid4()
    recognitions = RecognitionObjectRepository.get_by_toponym(test_db, invalid_id)
    assert len(recognitions) == 0


def test_get_by_module(
    test_db: DBSession,
    test_recognition_object: RecognitionObject,
    test_recognition_module: RecognitionModule,
):
    """Test getting recognition objects by module ID."""
    # Create another toponym
    toponym_create = ToponymCreate(
        start=40, end=45, document_id=test_recognition_object.toponym.document_id
    )

    # Create the toponym
    toponym = ToponymRepository.create(test_db, toponym_create)

    # Create another recognition object for the same module
    recognition_create = RecognitionObjectCreate(
        module_id=test_recognition_module.id, toponym_id=toponym.id
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


def test_get_all(test_db: DBSession, test_recognition_object: RecognitionObject):
    """Test getting all recognition objects."""
    # Create another recognition object
    recognition_create = RecognitionObjectCreate(
        module_id=test_recognition_object.module_id,
        toponym_id=test_recognition_object.toponym_id,
    )

    # Create the recognition object
    RecognitionObjectRepository.create(test_db, recognition_create)

    # Get all recognition objects
    recognitions = RecognitionObjectRepository.get_all(test_db)
    assert len(recognitions) >= 2


def test_update(test_db: DBSession, test_recognition_object: RecognitionObject):
    """Test updating a recognition object."""
    # Create a new module
    module_create = RecognitionModuleCreate(name="updated-module")
    module = RecognitionModule(name=module_create.name)
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


def test_delete(test_db: DBSession, test_recognition_object: RecognitionObject):
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
