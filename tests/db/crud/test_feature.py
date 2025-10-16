from sqlmodel import Session

from geoparser.db.crud import FeatureRepository
from geoparser.db.models import (
    Feature,
    FeatureCreate,
    FeatureUpdate,
    Gazetteer,
    Source,
)


def test_create(test_db: Session, test_source: Source):
    """Test creating a feature."""
    # Create a feature using the create model with all required fields
    feature_create = FeatureCreate(
        source_id=test_source.id,
        location_id_value="123456",
    )

    # Create the feature
    created_feature = FeatureRepository.create(test_db, feature_create)

    assert created_feature.id is not None
    assert created_feature.source_id == test_source.id
    assert created_feature.location_id_value == "123456"

    # Verify it was saved to the database
    db_feature = test_db.get(Feature, created_feature.id)
    assert db_feature is not None
    assert db_feature.source_id == test_source.id
    assert db_feature.location_id_value == "123456"


def test_get(test_db: Session, test_feature: Feature):
    """Test getting a feature by ID."""
    # Test with valid ID
    feature = FeatureRepository.get(test_db, test_feature.id)
    assert feature is not None
    assert feature.id == test_feature.id
    assert feature.source_id == test_feature.source_id
    assert feature.location_id_value == test_feature.location_id_value

    # Test with invalid ID
    invalid_id = 999999
    feature = FeatureRepository.get(test_db, invalid_id)
    assert feature is None


def test_get_by_gazetteer(test_db: Session, test_feature: Feature, test_source: Source):
    """Test getting features by gazetteer name."""
    # Create another feature for the same source
    feature_create = FeatureCreate(
        source_id=test_source.id,
        location_id_value="654321",
    )

    # Create the feature
    FeatureRepository.create(test_db, feature_create)

    # Get features by gazetteer
    features = FeatureRepository.get_by_gazetteer(test_db, "test-gazetteer")
    assert len(features) == 2
    assert any(f.location_id_value == "123456" for f in features)
    assert any(f.location_id_value == "654321" for f in features)

    # Test with non-existent gazetteer
    features = FeatureRepository.get_by_gazetteer(test_db, "non-existent-gazetteer")
    assert len(features) == 0


def test_get_by_gazetteer_and_identifier(
    test_db: Session, test_feature: Feature, test_gazetteer: Gazetteer
):
    """Test getting a feature by gazetteer name and identifier value."""
    # Create another gazetteer and source

    another_gazetteer = Gazetteer(name="another-gazetteer")
    test_db.add(another_gazetteer)
    test_db.commit()
    test_db.refresh(another_gazetteer)

    another_source = Source(
        name="another_table",
        location_id_name="another_id",
        gazetteer_id=another_gazetteer.id,
    )
    test_db.add(another_source)
    test_db.commit()
    test_db.refresh(another_source)

    # Create a feature for the different source with same identifier value
    feature_create = FeatureCreate(
        source_id=another_source.id,
        location_id_value="123456",  # Same identifier value, different gazetteer
    )

    # Create the feature
    FeatureRepository.create(test_db, feature_create)

    # Test with valid gazetteer and identifier
    feature = FeatureRepository.get_by_gazetteer_and_identifier(
        test_db, "test-gazetteer", "123456"
    )
    assert feature is not None
    assert feature.id == test_feature.id
    assert feature.source.gazetteer.name == "test-gazetteer"
    assert feature.location_id_value == "123456"

    # Test with different gazetteer, same identifier
    feature = FeatureRepository.get_by_gazetteer_and_identifier(
        test_db, "another-gazetteer", "123456"
    )
    assert feature is not None
    assert feature.source.gazetteer.name == "another-gazetteer"
    assert feature.location_id_value == "123456"

    # Test with non-existent gazetteer
    feature = FeatureRepository.get_by_gazetteer_and_identifier(
        test_db, "non-existent-gazetteer", "123456"
    )
    assert feature is None

    # Test with non-existent identifier
    feature = FeatureRepository.get_by_gazetteer_and_identifier(
        test_db, "test-gazetteer", "non-existent-id"
    )
    assert feature is None


def test_get_all(test_db: Session, test_feature: Feature):
    """Test getting all features."""
    # Create another gazetteer and source
    another_gazetteer = Gazetteer(name="another-gazetteer")
    test_db.add(another_gazetteer)
    test_db.commit()
    test_db.refresh(another_gazetteer)

    another_source = Source(
        name="another_table",
        location_id_name="another_id",
        gazetteer_id=another_gazetteer.id,
    )
    test_db.add(another_source)
    test_db.commit()
    test_db.refresh(another_source)

    # Create a feature for the different source
    feature_create = FeatureCreate(
        source_id=another_source.id,
        location_id_value="654321",
    )

    # Create the feature
    FeatureRepository.create(test_db, feature_create)

    # Get all features
    features = FeatureRepository.get_all(test_db)
    assert len(features) == 2
    assert any(f.source.gazetteer.name == "test-gazetteer" for f in features)
    assert any(f.source.gazetteer.name == "another-gazetteer" for f in features)


def test_update(test_db: Session, test_feature: Feature, test_source: Source):
    """Test updating a feature."""
    # Update the feature
    feature_update = FeatureUpdate(
        id=test_feature.id,
        source_id=test_source.id,
        location_id_value="updated-value",
    )
    updated_feature = FeatureRepository.update(
        test_db, db_obj=test_feature, obj_in=feature_update
    )

    assert updated_feature.id == test_feature.id
    assert updated_feature.source_id == test_source.id
    assert updated_feature.location_id_value == "updated-value"

    # Verify it was updated in the database
    db_feature = test_db.get(Feature, test_feature.id)
    assert db_feature is not None
    assert db_feature.source_id == test_source.id
    assert db_feature.location_id_value == "updated-value"


def test_delete(test_db: Session, test_feature: Feature):
    """Test deleting a feature."""
    # Delete the feature
    deleted_feature = FeatureRepository.delete(test_db, id=test_feature.id)

    assert deleted_feature is not None
    assert deleted_feature.id == test_feature.id

    # Verify it was deleted from the database
    db_feature = test_db.get(Feature, test_feature.id)
    assert db_feature is None
