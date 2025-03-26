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
        "module_name": "test-recognition-module",
        "model": "en_core_web_sm",
        "threshold": 0.8,
    }

    module_create = RecognitionModuleCreate(config=config)
    module = RecognitionModule(config=module_create.config)

    created_module = RecognitionModuleRepository.create(test_db, module)

    assert created_module.id is not None
    assert created_module.config == config
    assert created_module.config["module_name"] == "test-recognition-module"

    # Verify it was saved to the database
    db_module = test_db.get(RecognitionModule, created_module.id)
    assert db_module is not None
    assert db_module.config == config
    assert db_module.config["module_name"] == "test-recognition-module"


def test_get(test_db: Session, test_recognition_module: RecognitionModule):
    """Test getting a recognition module by ID."""
    # Test with valid ID
    module = RecognitionModuleRepository.get(test_db, test_recognition_module.id)
    assert module is not None
    assert module.id == test_recognition_module.id
    assert module.config == test_recognition_module.config

    # Test with invalid ID
    invalid_id = uuid.uuid4()
    module = RecognitionModuleRepository.get(test_db, invalid_id)
    assert module is None


def test_get_by_config(test_db: Session):
    """Test getting a recognition module by config."""
    # Create modules with the same module_name but different configs
    config1 = {
        "module_name": "same-name-module",
        "model": "en_core_web_sm",
        "threshold": 0.8,
    }

    config2 = {
        "module_name": "same-name-module",
        "model": "en_core_web_lg",
        "threshold": 0.7,
    }

    module_create1 = RecognitionModuleCreate(config=config1)
    module1 = RecognitionModule(config=module_create1.config)
    test_db.add(module1)

    module_create2 = RecognitionModuleCreate(config=config2)
    module2 = RecognitionModule(config=module_create2.config)
    test_db.add(module2)

    test_db.commit()
    test_db.refresh(module1)
    test_db.refresh(module2)

    # Test with valid config
    retrieved_module = RecognitionModuleRepository.get_by_config(test_db, config1)
    assert retrieved_module is not None
    assert retrieved_module.id == module1.id
    assert retrieved_module.config == config1

    # Test with different config
    retrieved_module = RecognitionModuleRepository.get_by_config(test_db, config2)
    assert retrieved_module is not None
    assert retrieved_module.id == module2.id
    assert retrieved_module.config == config2

    # Test with non-existent config
    non_existent_config = {
        "module_name": "same-name-module",
        "model": "non_existent_model",
        "threshold": 0.5,
    }
    retrieved_module = RecognitionModuleRepository.get_by_config(
        test_db, non_existent_config
    )
    assert retrieved_module is None

    # Test with missing module_name
    incomplete_config = {"model": "en_core_web_sm"}
    try:
        RecognitionModuleRepository.get_by_config(test_db, incomplete_config)
        assert False, "Should have raised ValueError for missing module_name"
    except ValueError:
        pass  # Expected


def test_get_all(test_db: Session, test_recognition_module: RecognitionModule):
    """Test getting all recognition modules."""
    # Create another module
    config = {"module_name": "another-recognition-module", "model": "en_core_web_md"}

    module_create = RecognitionModuleCreate(config=config)
    module = RecognitionModule(config=module_create.config)
    test_db.add(module)
    test_db.commit()

    # Get all modules
    modules = RecognitionModuleRepository.get_all(test_db)
    assert len(modules) >= 2
    assert any(
        m.config["module_name"] == test_recognition_module.config["module_name"]
        for m in modules
    )
    assert any(m.config["module_name"] == "another-recognition-module" for m in modules)


def test_update(test_db: Session, test_recognition_module: RecognitionModule):
    """Test updating a recognition module."""
    # Update the module
    updated_config = {
        "module_name": "updated-recognition-module",
        "model": "updated-model",
        "threshold": 0.9,
    }

    module_update = RecognitionModuleUpdate(
        id=test_recognition_module.id, config=updated_config
    )
    updated_module = RecognitionModuleRepository.update(
        test_db, db_obj=test_recognition_module, obj_in=module_update
    )

    assert updated_module.id == test_recognition_module.id
    assert updated_module.config == updated_config

    # Verify it was updated in the database
    db_module = test_db.get(RecognitionModule, test_recognition_module.id)
    assert db_module is not None
    assert db_module.config == updated_config


def test_delete(test_db: Session, test_recognition_module: RecognitionModule):
    """Test deleting a recognition module."""
    # Create a new module to delete
    config = {"module_name": "module-to-delete", "model": "to-be-deleted"}

    module_create = RecognitionModuleCreate(config=config)
    module = RecognitionModule(config=module_create.config)
    test_db.add(module)
    test_db.commit()
    test_db.refresh(module)

    # Delete the module
    deleted_module = RecognitionModuleRepository.delete(test_db, id=module.id)

    assert deleted_module is not None
    assert deleted_module.id == module.id
    assert deleted_module.config == config

    # Verify it was deleted from the database
    db_module = test_db.get(RecognitionModule, module.id)
    assert db_module is None
