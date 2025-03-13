import uuid

import pytest
from sqlmodel import Session as DBSession

from geoparser.db.crud import RecognitionRepository, ToponymRepository
from geoparser.db.models import (
    Recognition,
    RecognitionCreate,
    RecognitionModule,
    RecognitionModuleCreate,
    RecognitionUpdate,
    Toponym,
    ToponymCreate,
)


def test_create(
    test_db: DBSession,
    test_toponym: Toponym,
    test_recognition_module: RecognitionModule,
):
    """Test creating a recognition."""
    # Create a recognition using the create model with all required fields
    recognition_create = RecognitionCreate(
        module_id=test_recognition_module.id, toponym_id=test_toponym.id
    )

    # Create the recognition
    created_recognition = RecognitionRepository.create(test_db, recognition_create)

    assert created_recognition.id is not None
    assert created_recognition.toponym_id == test_toponym.id
    assert created_recognition.module_id == test_recognition_module.id

    # Verify it was saved to the database
    db_recognition = test_db.get(Recognition, created_recognition.id)
    assert db_recognition is not None
    assert db_recognition.toponym_id == test_toponym.id
    assert db_recognition.module_id == test_recognition_module.id


def test_get(test_db: DBSession, test_recognition: Recognition):
    """Test getting a recognition by ID."""
    # Test with valid ID
    recognition = RecognitionRepository.get(test_db, test_recognition.id)
    assert recognition is not None
    assert recognition.id == test_recognition.id
    assert recognition.toponym_id == test_recognition.toponym_id
    assert recognition.module_id == test_recognition.module_id

    # Test with invalid ID
    invalid_id = uuid.uuid4()
    recognition = RecognitionRepository.get(test_db, invalid_id)
    assert recognition is None


def test_get_by_toponym(
    test_db: DBSession,
    test_toponym: Toponym,
    test_recognition: Recognition,
    test_recognition_module: RecognitionModule,
):
    """Test getting recognitions by toponym ID."""
    # Create another recognition module
    module_create = RecognitionModuleCreate(name="another-recognition-module")
    module = RecognitionModule(name=module_create.name)
    test_db.add(module)
    test_db.commit()
    test_db.refresh(module)

    # Create another recognition for the same toponym
    recognition_create = RecognitionCreate(
        module_id=module.id, toponym_id=test_toponym.id
    )

    # Create the recognition
    RecognitionRepository.create(test_db, recognition_create)

    # Get recognitions by toponym
    recognitions = RecognitionRepository.get_by_toponym(test_db, test_toponym.id)
    assert len(recognitions) == 2
    assert any(r.module_id == test_recognition_module.id for r in recognitions)
    assert any(r.module_id == module.id for r in recognitions)

    # Test with invalid toponym ID
    invalid_id = uuid.uuid4()
    recognitions = RecognitionRepository.get_by_toponym(test_db, invalid_id)
    assert len(recognitions) == 0


def test_get_by_module(
    test_db: DBSession,
    test_recognition: Recognition,
    test_recognition_module: RecognitionModule,
):
    """Test getting recognitions by module ID."""
    # Create another toponym
    toponym_create = ToponymCreate(
        start=40, end=45, document_id=test_recognition.toponym.document_id
    )

    # Create the toponym
    toponym = ToponymRepository.create(test_db, toponym_create)

    # Create another recognition for the same module
    recognition_create = RecognitionCreate(
        module_id=test_recognition_module.id, toponym_id=toponym.id
    )

    # Create the recognition
    RecognitionRepository.create(test_db, recognition_create)

    # Get recognitions by module
    recognitions = RecognitionRepository.get_by_module(
        test_db, test_recognition_module.id
    )
    assert len(recognitions) == 2

    # Test with invalid module ID
    invalid_id = uuid.uuid4()
    recognitions = RecognitionRepository.get_by_module(test_db, invalid_id)
    assert len(recognitions) == 0


def test_get_all(test_db: DBSession, test_recognition: Recognition):
    """Test getting all recognitions."""
    # Create another recognition
    recognition_create = RecognitionCreate(
        module_id=test_recognition.module_id, toponym_id=test_recognition.toponym_id
    )

    # Create the recognition
    RecognitionRepository.create(test_db, recognition_create)

    # Get all recognitions
    recognitions = RecognitionRepository.get_all(test_db)
    assert len(recognitions) >= 2


def test_update(test_db: DBSession, test_recognition: Recognition):
    """Test updating a recognition."""
    # Create a new module
    module_create = RecognitionModuleCreate(name="updated-module")
    module = RecognitionModule(name=module_create.name)
    test_db.add(module)
    test_db.commit()
    test_db.refresh(module)

    # Update the recognition
    recognition_update = RecognitionUpdate(id=test_recognition.id, module_id=module.id)
    updated_recognition = RecognitionRepository.update(
        test_db, db_obj=test_recognition, obj_in=recognition_update
    )

    assert updated_recognition.id == test_recognition.id
    assert updated_recognition.module_id == module.id

    # Verify it was updated in the database
    db_recognition = test_db.get(Recognition, test_recognition.id)
    assert db_recognition is not None
    assert db_recognition.module_id == module.id


def test_delete(test_db: DBSession, test_recognition: Recognition):
    """Test deleting a recognition."""
    # Delete the recognition
    deleted_recognition = RecognitionRepository.delete(test_db, id=test_recognition.id)

    assert deleted_recognition is not None
    assert deleted_recognition.id == test_recognition.id

    # Verify it was deleted from the database
    db_recognition = test_db.get(Recognition, test_recognition.id)
    assert db_recognition is None
