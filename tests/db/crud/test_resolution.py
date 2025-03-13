import uuid

from sqlmodel import Session as DBSession

from geoparser.db.crud import LocationRepository, ResolutionRepository
from geoparser.db.models import (
    Location,
    LocationCreate,
    Resolution,
    ResolutionCreate,
    ResolutionModule,
    ResolutionModuleCreate,
    ResolutionUpdate,
)


def test_create(
    test_db: DBSession,
    test_location: Location,
    test_resolution_module: ResolutionModule,
):
    """Test creating a resolution."""
    # Create a resolution using the create model with all required fields
    resolution_create = ResolutionCreate(
        module_id=test_resolution_module.id, location_id=test_location.id
    )

    # Create the resolution
    created_resolution = ResolutionRepository.create(test_db, resolution_create)

    assert created_resolution.id is not None
    assert created_resolution.location_id == test_location.id
    assert created_resolution.module_id == test_resolution_module.id

    # Verify it was saved to the database
    db_resolution = test_db.get(Resolution, created_resolution.id)
    assert db_resolution is not None
    assert db_resolution.location_id == test_location.id
    assert db_resolution.module_id == test_resolution_module.id


def test_get(test_db: DBSession, test_resolution: Resolution):
    """Test getting a resolution by ID."""
    # Test with valid ID
    resolution = ResolutionRepository.get(test_db, test_resolution.id)
    assert resolution is not None
    assert resolution.id == test_resolution.id
    assert resolution.location_id == test_resolution.location_id
    assert resolution.module_id == test_resolution.module_id

    # Test with invalid ID
    invalid_id = uuid.uuid4()
    resolution = ResolutionRepository.get(test_db, invalid_id)
    assert resolution is None


def test_get_by_location(
    test_db: DBSession,
    test_location: Location,
    test_resolution: Resolution,
    test_resolution_module: ResolutionModule,
):
    """Test getting resolutions by location ID."""
    # Create another resolution module
    module_create = ResolutionModuleCreate(name="another-resolution-module")
    module = ResolutionModule(name=module_create.name)
    test_db.add(module)
    test_db.commit()
    test_db.refresh(module)

    # Create another resolution for the same location
    resolution_create = ResolutionCreate(
        module_id=module.id, location_id=test_location.id
    )

    # Create the resolution
    ResolutionRepository.create(test_db, resolution_create)

    # Get resolutions by location
    resolutions = ResolutionRepository.get_by_location(test_db, test_location.id)
    assert len(resolutions) == 2
    assert any(r.module_id == test_resolution_module.id for r in resolutions)
    assert any(r.module_id == module.id for r in resolutions)

    # Test with invalid location ID
    invalid_id = uuid.uuid4()
    resolutions = ResolutionRepository.get_by_location(test_db, invalid_id)
    assert len(resolutions) == 0


def test_get_by_module(
    test_db: DBSession,
    test_resolution: Resolution,
    test_resolution_module: ResolutionModule,
):
    """Test getting resolutions by module ID."""
    # Create another location
    location_create = LocationCreate(
        location_id="another-location",
        confidence=0.7,
        toponym_id=test_resolution.location.toponym_id,
    )

    # Create the location
    location = LocationRepository.create(test_db, location_create)

    # Create another resolution for the same module
    resolution_create = ResolutionCreate(
        module_id=test_resolution_module.id, location_id=location.id
    )

    # Create the resolution
    ResolutionRepository.create(test_db, resolution_create)

    # Get resolutions by module
    resolutions = ResolutionRepository.get_by_module(test_db, test_resolution_module.id)
    assert len(resolutions) == 2

    # Test with invalid module ID
    invalid_id = uuid.uuid4()
    resolutions = ResolutionRepository.get_by_module(test_db, invalid_id)
    assert len(resolutions) == 0


def test_get_all(test_db: DBSession, test_resolution: Resolution):
    """Test getting all resolutions."""
    # Create another resolution
    resolution_create = ResolutionCreate(
        module_id=test_resolution.module_id, location_id=test_resolution.location_id
    )

    # Create the resolution
    ResolutionRepository.create(test_db, resolution_create)

    # Get all resolutions
    resolutions = ResolutionRepository.get_all(test_db)
    assert len(resolutions) >= 2


def test_update(test_db: DBSession, test_resolution: Resolution):
    """Test updating a resolution."""
    # Create a new module
    module_create = ResolutionModuleCreate(name="updated-module")
    module = ResolutionModule(name=module_create.name)
    test_db.add(module)
    test_db.commit()
    test_db.refresh(module)

    # Update the resolution
    resolution_update = ResolutionUpdate(id=test_resolution.id, module_id=module.id)
    updated_resolution = ResolutionRepository.update(
        test_db, db_obj=test_resolution, obj_in=resolution_update
    )

    assert updated_resolution.id == test_resolution.id
    assert updated_resolution.module_id == module.id

    # Verify it was updated in the database
    db_resolution = test_db.get(Resolution, test_resolution.id)
    assert db_resolution is not None
    assert db_resolution.module_id == module.id


def test_delete(test_db: DBSession, test_resolution: Resolution):
    """Test deleting a resolution."""
    # Delete the resolution
    deleted_resolution = ResolutionRepository.delete(test_db, id=test_resolution.id)

    assert deleted_resolution is not None
    assert deleted_resolution.id == test_resolution.id

    # Verify it was deleted from the database
    db_resolution = test_db.get(Resolution, test_resolution.id)
    assert db_resolution is None
