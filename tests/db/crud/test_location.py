import uuid

from sqlmodel import Session as DBSession

from geoparser.db.crud import LocationRepository
from geoparser.db.models import Location, LocationCreate, LocationUpdate, Toponym


def test_create(test_db: DBSession, test_toponym: Toponym):
    """Test creating a location."""
    # Create a location using the create model with all required fields
    location_create = LocationCreate(
        location_id="654321", confidence=0.8, toponym_id=test_toponym.id
    )

    # Create the location
    created_location = LocationRepository.create(test_db, location_create)

    assert created_location.id is not None
    assert created_location.location_id == "654321"
    assert created_location.confidence == 0.8
    assert created_location.toponym_id == test_toponym.id

    # Verify it was saved to the database
    db_location = test_db.get(Location, created_location.id)
    assert db_location is not None
    assert db_location.location_id == "654321"
    assert db_location.confidence == 0.8
    assert db_location.toponym_id == test_toponym.id


def test_get(test_db: DBSession, test_location: Location):
    """Test getting a location by ID."""
    # Test with valid ID
    location = LocationRepository.get(test_db, test_location.id)
    assert location is not None
    assert location.id == test_location.id
    assert location.location_id == test_location.location_id
    assert location.confidence == test_location.confidence

    # Test with invalid ID
    invalid_id = uuid.uuid4()
    location = LocationRepository.get(test_db, invalid_id)
    assert location is None


def test_get_by_toponym(
    test_db: DBSession, test_toponym: Toponym, test_location: Location
):
    """Test getting locations by toponym ID."""
    # Create another location for the same toponym
    location_create = LocationCreate(
        location_id="654321", confidence=0.8, toponym_id=test_toponym.id
    )

    # Create the location
    LocationRepository.create(test_db, location_create)

    # Get locations by toponym
    locations = LocationRepository.get_by_toponym(test_db, test_toponym.id)
    assert len(locations) == 2
    assert any(l.location_id == "123456" for l in locations)
    assert any(l.location_id == "654321" for l in locations)

    # Test with invalid toponym ID
    invalid_id = uuid.uuid4()
    locations = LocationRepository.get_by_toponym(test_db, invalid_id)
    assert len(locations) == 0


def test_get_all(test_db: DBSession, test_location: Location):
    """Test getting all locations."""
    # Create another location
    location_create = LocationCreate(
        location_id="654321", confidence=0.8, toponym_id=test_location.toponym_id
    )

    # Create the location
    LocationRepository.create(test_db, location_create)

    # Get all locations
    locations = LocationRepository.get_all(test_db)
    assert len(locations) == 2
    assert any(l.location_id == "123456" for l in locations)
    assert any(l.location_id == "654321" for l in locations)


def test_update(test_db: DBSession, test_location: Location):
    """Test updating a location."""
    # Update the location
    location_update = LocationUpdate(
        id=test_location.id, location_id="updated-id", confidence=0.95
    )
    updated_location = LocationRepository.update(
        test_db, db_obj=test_location, obj_in=location_update
    )

    assert updated_location.id == test_location.id
    assert updated_location.location_id == "updated-id"
    assert updated_location.confidence == 0.95

    # Verify it was updated in the database
    db_location = test_db.get(Location, test_location.id)
    assert db_location is not None
    assert db_location.location_id == "updated-id"
    assert db_location.confidence == 0.95


def test_delete(test_db: DBSession, test_location: Location):
    """Test deleting a location."""
    # Delete the location
    deleted_location = LocationRepository.delete(test_db, id=test_location.id)

    assert deleted_location is not None
    assert deleted_location.id == test_location.id

    # Verify it was deleted from the database
    db_location = test_db.get(Location, test_location.id)
    assert db_location is None
