from sqlmodel import Session

from geoparser.db.crud import FeatureRepository, NameRepository
from geoparser.db.models import (
    Feature,
    FeatureCreate,
    Name,
    NameCreate,
    NameUpdate,
)


def test_create(test_db: Session, test_feature: Feature):
    """Test creating a name."""
    # Create a name using the create model with all required fields
    name_create = NameCreate(
        text="Test Place",
        feature_id=test_feature.id,
    )

    # Create the name
    created_name = NameRepository.create(test_db, name_create)

    assert created_name.id is not None
    assert created_name.text == "Test Place"
    assert created_name.feature_id == test_feature.id

    # Verify it was saved to the database
    db_name = test_db.get(Name, created_name.id)
    assert db_name is not None
    assert db_name.text == "Test Place"
    assert db_name.feature_id == test_feature.id


def test_get(test_db: Session, test_feature: Feature):
    """Test getting a name by ID."""
    # Create a name first
    name_create = NameCreate(
        text="Test Place",
        feature_id=test_feature.id,
    )
    created_name = NameRepository.create(test_db, name_create)

    # Test with valid ID
    name = NameRepository.get(test_db, created_name.id)
    assert name is not None
    assert name.id == created_name.id
    assert name.text == created_name.text
    assert name.feature_id == created_name.feature_id

    # Test with invalid ID
    invalid_id = 999999
    name = NameRepository.get(test_db, invalid_id)
    assert name is None


def test_get_by_feature(test_db: Session, test_feature: Feature):
    """Test getting names by feature ID."""
    # Create multiple names for the same feature
    name_create1 = NameCreate(
        text="Primary Name",
        feature_id=test_feature.id,
    )
    name_create2 = NameCreate(
        text="Alternative Name",
        feature_id=test_feature.id,
    )

    # Create the names
    NameRepository.create(test_db, name_create1)
    NameRepository.create(test_db, name_create2)

    # Get names by feature
    names = NameRepository.get_by_feature(test_db, test_feature.id)
    assert len(names) == 2
    assert any(n.text == "Primary Name" for n in names)
    assert any(n.text == "Alternative Name" for n in names)

    # Test with non-existent feature ID
    names = NameRepository.get_by_feature(test_db, 999999)
    assert len(names) == 0


def test_get_by_name(test_db: Session, test_feature: Feature):
    """Test getting names by name text."""
    # Create another gazetteer, source and feature
    from geoparser.db.models import Gazetteer, Source

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

    feature_create = FeatureCreate(
        source_id=another_source.id,
        location_id_value="654321",
    )
    another_feature = FeatureRepository.create(test_db, feature_create)

    # Create names with the same text for different features
    name_create1 = NameCreate(
        text="Common Name",
        feature_id=test_feature.id,
    )
    name_create2 = NameCreate(
        text="Common Name",
        feature_id=another_feature.id,
    )

    # Create the names
    NameRepository.create(test_db, name_create1)
    NameRepository.create(test_db, name_create2)

    # Get names by text
    names = NameRepository.get_by_name(test_db, "Common Name")
    assert len(names) == 2
    assert any(n.feature_id == test_feature.id for n in names)
    assert any(n.feature_id == another_feature.id for n in names)

    # Test with non-existent name
    names = NameRepository.get_by_name(test_db, "Non-existent Place")
    assert len(names) == 0


def test_get_all(test_db: Session, test_feature: Feature):
    """Test getting all names."""
    # Create another gazetteer, source and feature
    from geoparser.db.models import Gazetteer, Source

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

    feature_create = FeatureCreate(
        source_id=another_source.id,
        location_id_value="654321",
    )
    another_feature = FeatureRepository.create(test_db, feature_create)

    # Create names for different features
    name_create1 = NameCreate(
        text="Place One",
        feature_id=test_feature.id,
    )
    name_create2 = NameCreate(
        text="Place Two",
        feature_id=another_feature.id,
    )

    # Create the names
    NameRepository.create(test_db, name_create1)
    NameRepository.create(test_db, name_create2)

    # Get all names
    names = NameRepository.get_all(test_db)
    assert len(names) == 2
    assert any(n.text == "Place One" for n in names)
    assert any(n.text == "Place Two" for n in names)


def test_update(test_db: Session, test_feature: Feature):
    """Test updating a name."""
    # Create another gazetteer, source and feature to update to
    from geoparser.db.models import Gazetteer, Source

    updated_gazetteer = Gazetteer(name="updated-gazetteer")
    test_db.add(updated_gazetteer)
    test_db.commit()
    test_db.refresh(updated_gazetteer)

    updated_source = Source(
        name="updated_table",
        location_id_name="updated_id",
        gazetteer_id=updated_gazetteer.id,
    )
    test_db.add(updated_source)
    test_db.commit()
    test_db.refresh(updated_source)

    feature_create = FeatureCreate(
        source_id=updated_source.id,
        location_id_value="updated-value",
    )
    updated_feature = FeatureRepository.create(test_db, feature_create)

    # Create a name first
    name_create = NameCreate(
        text="Original Name",
        feature_id=test_feature.id,
    )
    created_name = NameRepository.create(test_db, name_create)

    # Update the name
    name_update = NameUpdate(
        id=created_name.id,
        text="Updated Name",
        feature_id=updated_feature.id,
    )
    updated_name = NameRepository.update(
        test_db, db_obj=created_name, obj_in=name_update
    )

    assert updated_name.id == created_name.id
    assert updated_name.text == "Updated Name"
    assert updated_name.feature_id == updated_feature.id

    # Verify it was updated in the database
    db_name = test_db.get(Name, created_name.id)
    assert db_name is not None
    assert db_name.text == "Updated Name"
    assert db_name.feature_id == updated_feature.id


def test_delete(test_db: Session, test_feature: Feature):
    """Test deleting a name."""
    # Create a name first
    name_create = NameCreate(
        text="To Be Deleted",
        feature_id=test_feature.id,
    )
    created_name = NameRepository.create(test_db, name_create)

    # Delete the name
    deleted_name = NameRepository.delete(test_db, id=created_name.id)

    assert deleted_name is not None
    assert deleted_name.id == created_name.id

    # Verify it was deleted from the database
    db_name = test_db.get(Name, created_name.id)
    assert db_name is None
