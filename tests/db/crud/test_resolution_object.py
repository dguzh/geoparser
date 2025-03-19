import uuid

from sqlmodel import Session as DBSession

from geoparser.db.crud import LocationRepository, ResolutionObjectRepository
from geoparser.db.models import (
    Location,
    LocationCreate,
    ResolutionModule,
    ResolutionModuleCreate,
    ResolutionObject,
    ResolutionObjectCreate,
    ResolutionObjectUpdate,
)


def test_create(
    test_db: DBSession,
    test_location: Location,
    test_resolution_module: ResolutionModule,
):
    """Test creating a resolution object."""
    # Create a resolution object using the create model with all required fields
    resolution_create = ResolutionObjectCreate(
        module_id=test_resolution_module.id, location_id=test_location.id
    )

    # Create the resolution object
    created_resolution = ResolutionObjectRepository.create(test_db, resolution_create)

    assert created_resolution.id is not None
    assert created_resolution.location_id == test_location.id
    assert created_resolution.module_id == test_resolution_module.id

    # Verify it was saved to the database
    db_resolution = test_db.get(ResolutionObject, created_resolution.id)
    assert db_resolution is not None
    assert db_resolution.location_id == test_location.id
    assert db_resolution.module_id == test_resolution_module.id


def test_get(test_db: DBSession, test_resolution_object: ResolutionObject):
    """Test getting a resolution object by ID."""
    # Test with valid ID
    resolution = ResolutionObjectRepository.get(test_db, test_resolution_object.id)
    assert resolution is not None
    assert resolution.id == test_resolution_object.id
    assert resolution.location_id == test_resolution_object.location_id
    assert resolution.module_id == test_resolution_object.module_id

    # Test with invalid ID
    invalid_id = uuid.uuid4()
    resolution = ResolutionObjectRepository.get(test_db, invalid_id)
    assert resolution is None


def test_get_by_location(
    test_db: DBSession,
    test_location: Location,
    test_resolution_object: ResolutionObject,
    test_resolution_module: ResolutionModule,
):
    """Test getting resolution objects by location ID."""
    # Create another resolution module
    config = {"module_name": "another-resolution-module", "gazetteer": "test-gazetteer"}

    module_create = ResolutionModuleCreate(config=config)
    module = ResolutionModule(config=module_create.config)
    test_db.add(module)
    test_db.commit()
    test_db.refresh(module)

    # Create another resolution object for the same location
    resolution_create = ResolutionObjectCreate(
        module_id=module.id, location_id=test_location.id
    )

    # Create the resolution object
    ResolutionObjectRepository.create(test_db, resolution_create)

    # Get resolution objects by location
    resolutions = ResolutionObjectRepository.get_by_location(test_db, test_location.id)
    assert len(resolutions) == 2
    assert any(r.module_id == test_resolution_module.id for r in resolutions)
    assert any(r.module_id == module.id for r in resolutions)

    # Test with invalid location ID
    invalid_id = uuid.uuid4()
    resolutions = ResolutionObjectRepository.get_by_location(test_db, invalid_id)
    assert len(resolutions) == 0


def test_get_by_module(
    test_db: DBSession,
    test_resolution_object: ResolutionObject,
    test_resolution_module: ResolutionModule,
):
    """Test getting resolution objects by module ID."""
    # Create another location
    location_create = LocationCreate(
        location_id="another-location",
        confidence=0.7,
        toponym_id=test_resolution_object.location.toponym_id,
    )

    # Create the location
    location = LocationRepository.create(test_db, location_create)

    # Create another resolution object for the same module
    resolution_create = ResolutionObjectCreate(
        module_id=test_resolution_module.id, location_id=location.id
    )

    # Create the resolution object
    ResolutionObjectRepository.create(test_db, resolution_create)

    # Get resolution objects by module
    resolutions = ResolutionObjectRepository.get_by_module(
        test_db, test_resolution_module.id
    )
    assert len(resolutions) == 2

    # Test with invalid module ID
    invalid_id = uuid.uuid4()
    resolutions = ResolutionObjectRepository.get_by_module(test_db, invalid_id)
    assert len(resolutions) == 0


def test_get_all(test_db: DBSession, test_resolution_object: ResolutionObject):
    """Test getting all resolution objects."""
    # Create another resolution object
    resolution_create = ResolutionObjectCreate(
        module_id=test_resolution_object.module_id,
        location_id=test_resolution_object.location_id,
    )

    # Create the resolution object
    ResolutionObjectRepository.create(test_db, resolution_create)

    # Get all resolution objects
    resolutions = ResolutionObjectRepository.get_all(test_db)
    assert len(resolutions) >= 2


def test_update(test_db: DBSession, test_resolution_object: ResolutionObject):
    """Test updating a resolution object."""
    # Create a new module
    config = {"module_name": "updated-module", "gazetteer": "updated-gazetteer"}

    module_create = ResolutionModuleCreate(config=config)
    module = ResolutionModule(config=module_create.config)
    test_db.add(module)
    test_db.commit()
    test_db.refresh(module)

    # Update the resolution object
    resolution_update = ResolutionObjectUpdate(
        id=test_resolution_object.id, module_id=module.id
    )
    updated_resolution = ResolutionObjectRepository.update(
        test_db, db_obj=test_resolution_object, obj_in=resolution_update
    )

    assert updated_resolution.id == test_resolution_object.id
    assert updated_resolution.module_id == module.id

    # Verify it was updated in the database
    db_resolution = test_db.get(ResolutionObject, test_resolution_object.id)
    assert db_resolution is not None
    assert db_resolution.module_id == module.id


def test_delete(test_db: DBSession, test_resolution_object: ResolutionObject):
    """Test deleting a resolution object."""
    # Delete the resolution object
    deleted_resolution = ResolutionObjectRepository.delete(
        test_db, id=test_resolution_object.id
    )

    assert deleted_resolution is not None
    assert deleted_resolution.id == test_resolution_object.id

    # Verify it was deleted from the database
    db_resolution = test_db.get(ResolutionObject, test_resolution_object.id)
    assert db_resolution is None
