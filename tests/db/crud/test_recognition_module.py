import uuid

import pytest
from sqlmodel import Session as DBSession

from geoparser.db.crud import RecognitionModuleRepository
from geoparser.db.models import (
    RecognitionModule,
    RecognitionModuleCreate,
    RecognitionModuleUpdate,
)


def test_create(test_db: DBSession):
    """Test creating a recognition module."""
    module_create = RecognitionModuleCreate(name="test-recognition-module")
    module = RecognitionModule(name=module_create.name)

    created_module = RecognitionModuleRepository.create(test_db, module)

    assert created_module.id is not None
    assert created_module.name == "test-recognition-module"

    # Verify it was saved to the database
    db_module = test_db.get(RecognitionModule, created_module.id)
    assert db_module is not None
    assert db_module.name == "test-recognition-module"


def test_get(test_db: DBSession, test_recognition_module: RecognitionModule):
    """Test getting a recognition module by ID."""
    # Test with valid ID
    module = RecognitionModuleRepository.get(test_db, test_recognition_module.id)
    assert module is not None
    assert module.id == test_recognition_module.id
    assert module.name == test_recognition_module.name

    # Test with invalid ID
    invalid_id = uuid.uuid4()
    module = RecognitionModuleRepository.get(test_db, invalid_id)
    assert module is None


def test_get_by_name(test_db: DBSession, test_recognition_module: RecognitionModule):
    """Test getting a recognition module by name."""
    # Test with valid name
    module = RecognitionModuleRepository.get_by_name(
        test_db, test_recognition_module.name
    )
    assert module is not None
    assert module.id == test_recognition_module.id
    assert module.name == test_recognition_module.name

    # Test with invalid name
    invalid_name = "non-existent-module"
    module = RecognitionModuleRepository.get_by_name(test_db, invalid_name)
    assert module is None


def test_get_all(test_db: DBSession, test_recognition_module: RecognitionModule):
    """Test getting all recognition modules."""
    # Create another module
    module_create = RecognitionModuleCreate(name="another-recognition-module")
    module = RecognitionModule(name=module_create.name)
    test_db.add(module)
    test_db.commit()

    # Get all modules
    modules = RecognitionModuleRepository.get_all(test_db)
    assert len(modules) >= 2
    assert any(m.name == test_recognition_module.name for m in modules)
    assert any(m.name == "another-recognition-module" for m in modules)


def test_update(test_db: DBSession, test_recognition_module: RecognitionModule):
    """Test updating a recognition module."""
    # Update the module
    module_update = RecognitionModuleUpdate(
        id=test_recognition_module.id, name="updated-recognition-module"
    )
    updated_module = RecognitionModuleRepository.update(
        test_db, db_obj=test_recognition_module, obj_in=module_update
    )

    assert updated_module.id == test_recognition_module.id
    assert updated_module.name == "updated-recognition-module"

    # Verify it was updated in the database
    db_module = test_db.get(RecognitionModule, test_recognition_module.id)
    assert db_module is not None
    assert db_module.name == "updated-recognition-module"


def test_delete(test_db: DBSession, test_recognition_module: RecognitionModule):
    """Test deleting a recognition module."""
    # Create a new module to delete
    module_create = RecognitionModuleCreate(name="module-to-delete")
    module = RecognitionModule(name=module_create.name)
    test_db.add(module)
    test_db.commit()
    test_db.refresh(module)

    # Delete the module
    deleted_module = RecognitionModuleRepository.delete(test_db, id=module.id)

    assert deleted_module is not None
    assert deleted_module.id == module.id
    assert deleted_module.name == "module-to-delete"

    # Verify it was deleted from the database
    db_module = test_db.get(RecognitionModule, module.id)
    assert db_module is None
