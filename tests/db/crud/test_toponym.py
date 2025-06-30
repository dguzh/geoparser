from sqlmodel import Session

from geoparser.db.crud import FeatureRepository, ToponymRepository
from geoparser.db.models import (
    Feature,
    FeatureCreate,
    Toponym,
    ToponymCreate,
    ToponymUpdate,
)


def test_create(test_db: Session, test_feature: Feature):
    """Test creating a toponym."""
    # Create a toponym using the create model with all required fields
    toponym_create = ToponymCreate(
        text="Test Place",
        feature_id=test_feature.id,
    )

    # Create the toponym
    created_toponym = ToponymRepository.create(test_db, toponym_create)

    assert created_toponym.id is not None
    assert created_toponym.text == "Test Place"
    assert created_toponym.feature_id == test_feature.id

    # Verify it was saved to the database
    db_toponym = test_db.get(Toponym, created_toponym.id)
    assert db_toponym is not None
    assert db_toponym.text == "Test Place"
    assert db_toponym.feature_id == test_feature.id


def test_get(test_db: Session, test_feature: Feature):
    """Test getting a toponym by ID."""
    # Create a toponym first
    toponym_create = ToponymCreate(
        text="Test Place",
        feature_id=test_feature.id,
    )
    created_toponym = ToponymRepository.create(test_db, toponym_create)

    # Test with valid ID
    toponym = ToponymRepository.get(test_db, created_toponym.id)
    assert toponym is not None
    assert toponym.id == created_toponym.id
    assert toponym.text == created_toponym.text
    assert toponym.feature_id == created_toponym.feature_id

    # Test with invalid ID
    invalid_id = 999999
    toponym = ToponymRepository.get(test_db, invalid_id)
    assert toponym is None


def test_get_by_feature(test_db: Session, test_feature: Feature):
    """Test getting toponyms by feature ID."""
    # Create multiple toponyms for the same feature
    toponym_create1 = ToponymCreate(
        text="Primary Name",
        feature_id=test_feature.id,
    )
    toponym_create2 = ToponymCreate(
        text="Alternative Name",
        feature_id=test_feature.id,
    )

    # Create the toponyms
    ToponymRepository.create(test_db, toponym_create1)
    ToponymRepository.create(test_db, toponym_create2)

    # Get toponyms by feature
    toponyms = ToponymRepository.get_by_feature(test_db, test_feature.id)
    assert len(toponyms) == 2
    assert any(t.text == "Primary Name" for t in toponyms)
    assert any(t.text == "Alternative Name" for t in toponyms)

    # Test with non-existent feature ID
    toponyms = ToponymRepository.get_by_feature(test_db, 999999)
    assert len(toponyms) == 0


def test_get_by_toponym(test_db: Session, test_feature: Feature):
    """Test getting toponyms by toponym text."""
    # Create another feature
    feature_create = FeatureCreate(
        gazetteer_name="another-gazetteer",
        table_name="another_table",
        identifier_name="another_id",
        identifier_value="654321",
    )
    another_feature = FeatureRepository.create(test_db, feature_create)

    # Create toponyms with the same text for different features
    toponym_create1 = ToponymCreate(
        text="Common Name",
        feature_id=test_feature.id,
    )
    toponym_create2 = ToponymCreate(
        text="Common Name",
        feature_id=another_feature.id,
    )

    # Create the toponyms
    ToponymRepository.create(test_db, toponym_create1)
    ToponymRepository.create(test_db, toponym_create2)

    # Get toponyms by text
    toponyms = ToponymRepository.get_by_toponym(test_db, "Common Name")
    assert len(toponyms) == 2
    assert any(t.feature_id == test_feature.id for t in toponyms)
    assert any(t.feature_id == another_feature.id for t in toponyms)

    # Test with non-existent toponym
    toponyms = ToponymRepository.get_by_toponym(test_db, "Non-existent Place")
    assert len(toponyms) == 0


def test_get_all(test_db: Session, test_feature: Feature):
    """Test getting all toponyms."""
    # Create another feature
    feature_create = FeatureCreate(
        gazetteer_name="another-gazetteer",
        table_name="another_table",
        identifier_name="another_id",
        identifier_value="654321",
    )
    another_feature = FeatureRepository.create(test_db, feature_create)

    # Create toponyms for different features
    toponym_create1 = ToponymCreate(
        text="Place One",
        feature_id=test_feature.id,
    )
    toponym_create2 = ToponymCreate(
        text="Place Two",
        feature_id=another_feature.id,
    )

    # Create the toponyms
    ToponymRepository.create(test_db, toponym_create1)
    ToponymRepository.create(test_db, toponym_create2)

    # Get all toponyms
    toponyms = ToponymRepository.get_all(test_db)
    assert len(toponyms) == 2
    assert any(t.text == "Place One" for t in toponyms)
    assert any(t.text == "Place Two" for t in toponyms)


def test_update(test_db: Session, test_feature: Feature):
    """Test updating a toponym."""
    # Create another feature to update to
    feature_create = FeatureCreate(
        gazetteer_name="updated-gazetteer",
        table_name="updated_table",
        identifier_name="updated_id",
        identifier_value="updated-value",
    )
    updated_feature = FeatureRepository.create(test_db, feature_create)

    # Create a toponym first
    toponym_create = ToponymCreate(
        text="Original Name",
        feature_id=test_feature.id,
    )
    created_toponym = ToponymRepository.create(test_db, toponym_create)

    # Update the toponym
    toponym_update = ToponymUpdate(
        id=created_toponym.id,
        text="Updated Name",
        feature_id=updated_feature.id,
    )
    updated_toponym = ToponymRepository.update(
        test_db, db_obj=created_toponym, obj_in=toponym_update
    )

    assert updated_toponym.id == created_toponym.id
    assert updated_toponym.text == "Updated Name"
    assert updated_toponym.feature_id == updated_feature.id

    # Verify it was updated in the database
    db_toponym = test_db.get(Toponym, created_toponym.id)
    assert db_toponym is not None
    assert db_toponym.text == "Updated Name"
    assert db_toponym.feature_id == updated_feature.id


def test_delete(test_db: Session, test_feature: Feature):
    """Test deleting a toponym."""
    # Create a toponym first
    toponym_create = ToponymCreate(
        text="To Be Deleted",
        feature_id=test_feature.id,
    )
    created_toponym = ToponymRepository.create(test_db, toponym_create)

    # Delete the toponym
    deleted_toponym = ToponymRepository.delete(test_db, id=created_toponym.id)

    assert deleted_toponym is not None
    assert deleted_toponym.id == created_toponym.id

    # Verify it was deleted from the database
    db_toponym = test_db.get(Toponym, created_toponym.id)
    assert db_toponym is None
