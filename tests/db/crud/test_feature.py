from sqlmodel import Session

from geoparser.db.crud import FeatureRepository
from geoparser.db.models import Feature, FeatureCreate, FeatureUpdate


def test_create(test_db: Session):
    """Test creating a feature."""
    # Create a feature using the create model with all required fields
    feature_create = FeatureCreate(
        gazetteer_name="test-gazetteer",
        table_name="test_table",
        identifier_name="test_id",
        identifier_value="123456",
    )

    # Create the feature
    created_feature = FeatureRepository.create(test_db, feature_create)

    assert created_feature.id is not None
    assert created_feature.gazetteer_name == "test-gazetteer"
    assert created_feature.table_name == "test_table"
    assert created_feature.identifier_name == "test_id"
    assert created_feature.identifier_value == "123456"

    # Verify it was saved to the database
    db_feature = test_db.get(Feature, created_feature.id)
    assert db_feature is not None
    assert db_feature.gazetteer_name == "test-gazetteer"
    assert db_feature.table_name == "test_table"
    assert db_feature.identifier_name == "test_id"
    assert db_feature.identifier_value == "123456"


def test_get(test_db: Session, test_feature: Feature):
    """Test getting a feature by ID."""
    # Test with valid ID
    feature = FeatureRepository.get(test_db, test_feature.id)
    assert feature is not None
    assert feature.id == test_feature.id
    assert feature.gazetteer_name == test_feature.gazetteer_name
    assert feature.table_name == test_feature.table_name
    assert feature.identifier_name == test_feature.identifier_name
    assert feature.identifier_value == test_feature.identifier_value

    # Test with invalid ID
    invalid_id = 999999
    feature = FeatureRepository.get(test_db, invalid_id)
    assert feature is None


def test_get_by_gazetteer(test_db: Session, test_feature: Feature):
    """Test getting features by gazetteer name."""
    # Create another feature for the same gazetteer
    feature_create = FeatureCreate(
        gazetteer_name="test-gazetteer",
        table_name="test_table",
        identifier_name="test_id",
        identifier_value="654321",
    )

    # Create the feature
    FeatureRepository.create(test_db, feature_create)

    # Get features by gazetteer
    features = FeatureRepository.get_by_gazetteer(test_db, "test-gazetteer")
    assert len(features) == 2
    assert any(f.identifier_value == "123456" for f in features)
    assert any(f.identifier_value == "654321" for f in features)

    # Test with non-existent gazetteer
    features = FeatureRepository.get_by_gazetteer(test_db, "non-existent-gazetteer")
    assert len(features) == 0


def test_get_by_gazetteer_and_identifier(test_db: Session, test_feature: Feature):
    """Test getting a feature by gazetteer name and identifier value."""
    # Create another feature for a different gazetteer
    feature_create = FeatureCreate(
        gazetteer_name="another-gazetteer",
        table_name="another_table",
        identifier_name="another_id",
        identifier_value="123456",  # Same identifier value, different gazetteer
    )

    # Create the feature
    FeatureRepository.create(test_db, feature_create)

    # Test with valid gazetteer and identifier
    feature = FeatureRepository.get_by_gazetteer_and_identifier(
        test_db, "test-gazetteer", "123456"
    )
    assert feature is not None
    assert feature.id == test_feature.id
    assert feature.gazetteer_name == "test-gazetteer"
    assert feature.identifier_value == "123456"

    # Test with different gazetteer, same identifier
    feature = FeatureRepository.get_by_gazetteer_and_identifier(
        test_db, "another-gazetteer", "123456"
    )
    assert feature is not None
    assert feature.gazetteer_name == "another-gazetteer"
    assert feature.identifier_value == "123456"

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
    # Create another feature
    feature_create = FeatureCreate(
        gazetteer_name="another-gazetteer",
        table_name="another_table",
        identifier_name="another_id",
        identifier_value="654321",
    )

    # Create the feature
    FeatureRepository.create(test_db, feature_create)

    # Get all features
    features = FeatureRepository.get_all(test_db)
    assert len(features) == 2
    assert any(f.gazetteer_name == "test-gazetteer" for f in features)
    assert any(f.gazetteer_name == "another-gazetteer" for f in features)


def test_update(test_db: Session, test_feature: Feature):
    """Test updating a feature."""
    # Update the feature
    feature_update = FeatureUpdate(
        id=test_feature.id,
        gazetteer_name="updated-gazetteer",
        table_name="updated_table",
        identifier_name="updated_id",
        identifier_value="updated-value",
    )
    updated_feature = FeatureRepository.update(
        test_db, db_obj=test_feature, obj_in=feature_update
    )

    assert updated_feature.id == test_feature.id
    assert updated_feature.gazetteer_name == "updated-gazetteer"
    assert updated_feature.table_name == "updated_table"
    assert updated_feature.identifier_name == "updated_id"
    assert updated_feature.identifier_value == "updated-value"

    # Verify it was updated in the database
    db_feature = test_db.get(Feature, test_feature.id)
    assert db_feature is not None
    assert db_feature.gazetteer_name == "updated-gazetteer"
    assert db_feature.table_name == "updated_table"
    assert db_feature.identifier_name == "updated_id"
    assert db_feature.identifier_value == "updated-value"


def test_delete(test_db: Session, test_feature: Feature):
    """Test deleting a feature."""
    # Delete the feature
    deleted_feature = FeatureRepository.delete(test_db, id=test_feature.id)

    assert deleted_feature is not None
    assert deleted_feature.id == test_feature.id

    # Verify it was deleted from the database
    db_feature = test_db.get(Feature, test_feature.id)
    assert db_feature is None
