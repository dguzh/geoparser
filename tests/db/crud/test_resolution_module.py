import uuid

import pytest
from sqlmodel import Session as DBSession

from geoparser.db.crud import ResolutionModuleRepository
from geoparser.db.models import (
    ResolutionModule,
    ResolutionModuleCreate,
    ResolutionModuleUpdate,
)


def test_create(test_db: DBSession):
    """Test creating a resolution module."""
    module_create = ResolutionModuleCreate(name="test-resolution-module")
    module = ResolutionModule(name=module_create.name)

    created_module = ResolutionModuleRepository.create(test_db, module)

    assert created_module.id is not None
    assert created_module.name == "test-resolution-module"

    # Verify it was saved to the database
    db_module = test_db.get(ResolutionModule, created_module.id)
    assert db_module is not None
    assert db_module.name == "test-resolution-module"


def test_get(test_db: DBSession, test_resolution_module: ResolutionModule):
    """Test getting a resolution module by ID."""
    # Test with valid ID
    module = ResolutionModuleRepository.get(test_db, test_resolution_module.id)
    assert module is not None
    assert module.id == test_resolution_module.id
    assert module.name == test_resolution_module.name

    # Test with invalid ID
    invalid_id = uuid.uuid4()
    module = ResolutionModuleRepository.get(test_db, invalid_id)
    assert module is None


def test_get_by_name(test_db: DBSession, test_resolution_module: ResolutionModule):
    """Test getting a resolution module by name."""
    # Test with valid name
    module = ResolutionModuleRepository.get_by_name(
        test_db, test_resolution_module.name
    )
    assert module is not None
    assert module.id == test_resolution_module.id
    assert module.name == test_resolution_module.name

    # Test with invalid name
    invalid_name = "non-existent-module"
    module = ResolutionModuleRepository.get_by_name(test_db, invalid_name)
    assert module is None


def test_get_all(test_db: DBSession, test_resolution_module: ResolutionModule):
    """Test getting all resolution modules."""
    # Create another module
    module_create = ResolutionModuleCreate(name="another-resolution-module")
    module = ResolutionModule(name=module_create.name)
    test_db.add(module)
    test_db.commit()

    # Get all modules
    modules = ResolutionModuleRepository.get_all(test_db)
    assert len(modules) >= 2
    assert any(m.name == test_resolution_module.name for m in modules)
    assert any(m.name == "another-resolution-module" for m in modules)


def test_update(test_db: DBSession, test_resolution_module: ResolutionModule):
    """Test updating a resolution module."""
    # Update the module
    module_update = ResolutionModuleUpdate(
        id=test_resolution_module.id, name="updated-resolution-module"
    )
    updated_module = ResolutionModuleRepository.update(
        test_db, db_obj=test_resolution_module, obj_in=module_update
    )

    assert updated_module.id == test_resolution_module.id
    assert updated_module.name == "updated-resolution-module"

    # Verify it was updated in the database
    db_module = test_db.get(ResolutionModule, test_resolution_module.id)
    assert db_module is not None
    assert db_module.name == "updated-resolution-module"


def test_delete(test_db: DBSession, test_resolution_module: ResolutionModule):
    """Test deleting a resolution module."""
    # Create a new module to delete
    module_create = ResolutionModuleCreate(name="module-to-delete")
    module = ResolutionModule(name=module_create.name)
    test_db.add(module)
    test_db.commit()
    test_db.refresh(module)

    # Delete the module
    deleted_module = ResolutionModuleRepository.delete(test_db, id=module.id)

    assert deleted_module is not None
    assert deleted_module.id == module.id
    assert deleted_module.name == "module-to-delete"

    # Verify it was deleted from the database
    db_module = test_db.get(ResolutionModule, module.id)
    assert db_module is None
