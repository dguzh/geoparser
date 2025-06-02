import uuid

from sqlmodel import Session

from geoparser.db.crud import FeatureRepository, LocationRepository
from geoparser.db.models import (
    Feature,
    FeatureCreate,
    Location,
    LocationCreate,
    LocationUpdate,
    Toponym,
)


def test_create(test_db: Session, test_toponym: Toponym, test_feature: Feature):
    """Test creating a location."""
    # Create a location using the create model with all required fields
    location_create = LocationCreate(
        toponym_id=test_toponym.id, feature_id=test_feature.id
    )

    # Create the location
    created_location = LocationRepository.create(test_db, location_create)

    assert created_location.id is not None
    assert created_location.toponym_id == test_toponym.id
    assert created_location.feature_id == test_feature.id

    # Verify it was saved to the database
    db_location = test_db.get(Location, created_location.id)
    assert db_location is not None
    assert db_location.toponym_id == test_toponym.id
    assert db_location.feature_id == test_feature.id


def test_get(test_db: Session, test_location: Location):
    """Test getting a location by ID."""
    # Test with valid ID
    location = LocationRepository.get(test_db, test_location.id)
    assert location is not None
    assert location.id == test_location.id
    assert location.toponym_id == test_location.toponym_id
    assert location.feature_id == test_location.feature_id

    # Test with invalid ID
    invalid_id = uuid.uuid4()
    location = LocationRepository.get(test_db, invalid_id)
    assert location is None


def test_get_by_toponym(
    test_db: Session, test_toponym: Toponym, test_location: Location
):
    """Test getting locations by toponym ID."""
    # Create another feature
    feature_create = FeatureCreate(
        gazetteer_name="another-gazetteer",
        table_name="another_table",
        identifier_name="another_id",
        identifier_value="654321",
    )
    another_feature = FeatureRepository.create(test_db, feature_create)

    # Create another location for the same toponym
    location_create = LocationCreate(
        toponym_id=test_toponym.id, feature_id=another_feature.id
    )

    # Create the location
    LocationRepository.create(test_db, location_create)

    # Get locations by toponym
    locations = LocationRepository.get_by_toponym(test_db, test_toponym.id)
    assert len(locations) == 2
    assert any(l.feature_id == test_location.feature_id for l in locations)
    assert any(l.feature_id == another_feature.id for l in locations)

    # Test with invalid toponym ID
    invalid_id = uuid.uuid4()
    locations = LocationRepository.get_by_toponym(test_db, invalid_id)
    assert len(locations) == 0


def test_get_all(test_db: Session, test_location: Location):
    """Test getting all locations."""
    # Create another feature
    feature_create = FeatureCreate(
        gazetteer_name="another-gazetteer",
        table_name="another_table",
        identifier_name="another_id",
        identifier_value="654321",
    )
    another_feature = FeatureRepository.create(test_db, feature_create)

    # Create another location
    location_create = LocationCreate(
        toponym_id=test_location.toponym_id, feature_id=another_feature.id
    )

    # Create the location
    LocationRepository.create(test_db, location_create)

    # Get all locations
    locations = LocationRepository.get_all(test_db)
    assert len(locations) == 2
    assert any(l.feature_id == test_location.feature_id for l in locations)
    assert any(l.feature_id == another_feature.id for l in locations)


def test_update(test_db: Session, test_location: Location):
    """Test updating a location."""
    # Create a new feature to update to
    feature_create = FeatureCreate(
        gazetteer_name="updated-gazetteer",
        table_name="updated_table",
        identifier_name="updated_id",
        identifier_value="updated-value",
    )
    updated_feature = FeatureRepository.create(test_db, feature_create)

    # Update the location
    location_update = LocationUpdate(id=test_location.id, feature_id=updated_feature.id)
    updated_location = LocationRepository.update(
        test_db, db_obj=test_location, obj_in=location_update
    )

    assert updated_location.id == test_location.id
    assert updated_location.feature_id == updated_feature.id

    # Verify it was updated in the database
    db_location = test_db.get(Location, test_location.id)
    assert db_location is not None
    assert db_location.feature_id == updated_feature.id


def test_delete(test_db: Session, test_location: Location):
    """Test deleting a location."""
    # Delete the location
    deleted_location = LocationRepository.delete(test_db, id=test_location.id)

    assert deleted_location is not None
    assert deleted_location.id == test_location.id

    # Verify it was deleted from the database
    db_location = test_db.get(Location, test_location.id)
    assert db_location is None
