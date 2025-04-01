import uuid

from sqlmodel import Session

from geoparser.db.crud import RecognitionModuleRepository
from geoparser.db.models import (
    RecognitionModule,
    RecognitionModuleCreate,
    RecognitionModuleUpdate,
)


def test_create(test_db: Session):
    """Test creating a recognition module."""
    config = {
        "model": "en_core_web_sm",
        "threshold": 0.8,
    }

    module_create = RecognitionModuleCreate(
        name="test-recognition-module", config=config
    )
    module = RecognitionModule(name=module_create.name, config=module_create.config)

    created_module = RecognitionModuleRepository.create(test_db, module)

    assert created_module.id is not None
    assert created_module.name == "test-recognition-module"
    assert created_module.config == config

    # Verify it was saved to the database
    db_module = test_db.get(RecognitionModule, created_module.id)
    assert db_module is not None
    assert db_module.name == "test-recognition-module"
    assert db_module.config == config


def test_get(test_db: Session, test_recognition_module: RecognitionModule):
    """Test getting a recognition module by ID."""
    # Test with valid ID
    module = RecognitionModuleRepository.get(test_db, test_recognition_module.id)
    assert module is not None
    assert module.id == test_recognition_module.id
    assert module.name == test_recognition_module.name
    assert module.config == test_recognition_module.config

    # Test with invalid ID
    invalid_id = uuid.uuid4()
    module = RecognitionModuleRepository.get(test_db, invalid_id)
    assert module is None


def test_get_by_name_and_config(test_db: Session):
    """Test getting a recognition module by name and config."""
    # Create modules with the same name but different configs
    config1 = {
        "model": "en_core_web_sm",
        "threshold": 0.8,
    }

    config2 = {
        "model": "en_core_web_lg",
        "threshold": 0.7,
    }

    module_create1 = RecognitionModuleCreate(name="same-name-module", config=config1)
    module1 = RecognitionModule(name=module_create1.name, config=module_create1.config)
    test_db.add(module1)

    module_create2 = RecognitionModuleCreate(name="same-name-module", config=config2)
    module2 = RecognitionModule(name=module_create2.name, config=module_create2.config)
    test_db.add(module2)

    test_db.commit()
    test_db.refresh(module1)
    test_db.refresh(module2)

    # Test with valid name and config
    retrieved_module = RecognitionModuleRepository.get_by_name_and_config(
        test_db, "same-name-module", config1
    )
    assert retrieved_module is not None
    assert retrieved_module.id == module1.id
    assert retrieved_module.name == "same-name-module"
    assert retrieved_module.config == config1

    # Test with different config
    retrieved_module = RecognitionModuleRepository.get_by_name_and_config(
        test_db, "same-name-module", config2
    )
    assert retrieved_module is not None
    assert retrieved_module.id == module2.id
    assert retrieved_module.name == "same-name-module"
    assert retrieved_module.config == config2

    # Test with non-existent config
    non_existent_config = {
        "model": "non_existent_model",
        "threshold": 0.5,
    }
    retrieved_module = RecognitionModuleRepository.get_by_name_and_config(
        test_db, "same-name-module", non_existent_config
    )
    assert retrieved_module is None

    # Test with non-existent name
    retrieved_module = RecognitionModuleRepository.get_by_name_and_config(
        test_db, "non-existent-module", config1
    )
    assert retrieved_module is None


def test_get_all(test_db: Session, test_recognition_module: RecognitionModule):
    """Test getting all recognition modules."""
    # Create another module
    config = {"model": "en_core_web_md"}

    module_create = RecognitionModuleCreate(
        name="another-recognition-module", config=config
    )
    module = RecognitionModule(name=module_create.name, config=module_create.config)
    test_db.add(module)
    test_db.commit()

    # Get all modules
    modules = RecognitionModuleRepository.get_all(test_db)
    assert len(modules) >= 2
    assert any(m.name == test_recognition_module.name for m in modules)
    assert any(m.name == "another-recognition-module" for m in modules)


def test_update(test_db: Session, test_recognition_module: RecognitionModule):
    """Test updating a recognition module."""
    # Update the module
    updated_config = {
        "model": "updated-model",
        "threshold": 0.9,
    }

    module_update = RecognitionModuleUpdate(
        id=test_recognition_module.id,
        name="updated-recognition-module",
        config=updated_config,
    )
    updated_module = RecognitionModuleRepository.update(
        test_db, db_obj=test_recognition_module, obj_in=module_update
    )

    assert updated_module.id == test_recognition_module.id
    assert updated_module.name == "updated-recognition-module"
    assert updated_module.config == updated_config

    # Verify it was updated in the database
    db_module = test_db.get(RecognitionModule, test_recognition_module.id)
    assert db_module is not None
    assert db_module.name == "updated-recognition-module"
    assert db_module.config == updated_config


def test_delete(test_db: Session, test_recognition_module: RecognitionModule):
    """Test deleting a recognition module."""
    # Create a new module to delete
    config = {"model": "to-be-deleted"}

    module_create = RecognitionModuleCreate(name="module-to-delete", config=config)
    module = RecognitionModule(name=module_create.name, config=module_create.config)
    test_db.add(module)
    test_db.commit()
    test_db.refresh(module)

    # Delete the module
    deleted_module = RecognitionModuleRepository.delete(test_db, id=module.id)

    assert deleted_module is not None
    assert deleted_module.id == module.id
    assert deleted_module.name == "module-to-delete"
    assert deleted_module.config == config

    # Verify it was deleted from the database
    db_module = test_db.get(RecognitionModule, module.id)
    assert db_module is None
