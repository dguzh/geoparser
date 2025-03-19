import uuid

from sqlmodel import Session as DBSession

from geoparser.db.crud import ResolutionModuleRepository
from geoparser.db.models import (
    ResolutionModule,
    ResolutionModuleCreate,
    ResolutionModuleUpdate,
)


def test_create(test_db: DBSession):
    """Test creating a resolution module."""
    config = {
        "module_name": "test-resolution-module",
        "gazetteer": "test-gazetteer",
        "max_results": 5,
    }

    module_create = ResolutionModuleCreate(config=config)
    module = ResolutionModule(config=module_create.config)

    created_module = ResolutionModuleRepository.create(test_db, module)

    assert created_module.id is not None
    assert created_module.config == config
    assert created_module.config["module_name"] == "test-resolution-module"

    # Verify it was saved to the database
    db_module = test_db.get(ResolutionModule, created_module.id)
    assert db_module is not None
    assert db_module.config == config
    assert db_module.config["module_name"] == "test-resolution-module"


def test_get(test_db: DBSession, test_resolution_module: ResolutionModule):
    """Test getting a resolution module by ID."""
    # Test with valid ID
    module = ResolutionModuleRepository.get(test_db, test_resolution_module.id)
    assert module is not None
    assert module.id == test_resolution_module.id
    assert module.config == test_resolution_module.config

    # Test with invalid ID
    invalid_id = uuid.uuid4()
    module = ResolutionModuleRepository.get(test_db, invalid_id)
    assert module is None


def test_get_by_config(test_db: DBSession):
    """Test getting a resolution module by config."""
    # Create modules with the same module_name but different configs
    config1 = {
        "module_name": "same-name-module",
        "gazetteer": "gazetteer1",
        "max_results": 5,
    }

    config2 = {
        "module_name": "same-name-module",
        "gazetteer": "gazetteer2",
        "max_results": 10,
    }

    module_create1 = ResolutionModuleCreate(config=config1)
    module1 = ResolutionModule(config=module_create1.config)
    test_db.add(module1)

    module_create2 = ResolutionModuleCreate(config=config2)
    module2 = ResolutionModule(config=module_create2.config)
    test_db.add(module2)

    test_db.commit()
    test_db.refresh(module1)
    test_db.refresh(module2)

    # Test with valid config
    retrieved_module = ResolutionModuleRepository.get_by_config(test_db, config1)
    assert retrieved_module is not None
    assert retrieved_module.id == module1.id
    assert retrieved_module.config == config1

    # Test with different config
    retrieved_module = ResolutionModuleRepository.get_by_config(test_db, config2)
    assert retrieved_module is not None
    assert retrieved_module.id == module2.id
    assert retrieved_module.config == config2

    # Test with non-existent config
    non_existent_config = {
        "module_name": "same-name-module",
        "gazetteer": "non_existent_gazetteer",
        "max_results": 15,
    }
    retrieved_module = ResolutionModuleRepository.get_by_config(
        test_db, non_existent_config
    )
    assert retrieved_module is None

    # Test with missing module_name
    incomplete_config = {"gazetteer": "gazetteer1"}
    try:
        ResolutionModuleRepository.get_by_config(test_db, incomplete_config)
        assert False, "Should have raised ValueError for missing module_name"
    except ValueError:
        pass  # Expected


def test_get_all(test_db: DBSession, test_resolution_module: ResolutionModule):
    """Test getting all resolution modules."""
    # Create another module
    config = {
        "module_name": "another-resolution-module",
        "gazetteer": "another-gazetteer",
    }

    module_create = ResolutionModuleCreate(config=config)
    module = ResolutionModule(config=module_create.config)
    test_db.add(module)
    test_db.commit()

    # Get all modules
    modules = ResolutionModuleRepository.get_all(test_db)
    assert len(modules) >= 2
    assert any(
        m.config["module_name"] == test_resolution_module.config["module_name"]
        for m in modules
    )
    assert any(m.config["module_name"] == "another-resolution-module" for m in modules)


def test_update(test_db: DBSession, test_resolution_module: ResolutionModule):
    """Test updating a resolution module."""
    # Update the module
    updated_config = {
        "module_name": "updated-resolution-module",
        "gazetteer": "updated-gazetteer",
        "max_results": 20,
    }

    module_update = ResolutionModuleUpdate(
        id=test_resolution_module.id, config=updated_config
    )
    updated_module = ResolutionModuleRepository.update(
        test_db, db_obj=test_resolution_module, obj_in=module_update
    )

    assert updated_module.id == test_resolution_module.id
    assert updated_module.config == updated_config

    # Verify it was updated in the database
    db_module = test_db.get(ResolutionModule, test_resolution_module.id)
    assert db_module is not None
    assert db_module.config == updated_config


def test_delete(test_db: DBSession, test_resolution_module: ResolutionModule):
    """Test deleting a resolution module."""
    # Create a new module to delete
    config = {"module_name": "module-to-delete", "gazetteer": "to-be-deleted"}

    module_create = ResolutionModuleCreate(config=config)
    module = ResolutionModule(config=module_create.config)
    test_db.add(module)
    test_db.commit()
    test_db.refresh(module)

    # Delete the module
    deleted_module = ResolutionModuleRepository.delete(test_db, id=module.id)

    assert deleted_module is not None
    assert deleted_module.id == module.id
    assert deleted_module.config == config

    # Verify it was deleted from the database
    db_module = test_db.get(ResolutionModule, module.id)
    assert db_module is None
