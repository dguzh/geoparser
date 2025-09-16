import uuid

from sqlmodel import Session

from geoparser.db.crud import FeatureRepository, ReferentRepository
from geoparser.db.models import (
    Feature,
    FeatureCreate,
    Reference,
    Referent,
    ReferentCreate,
    ReferentUpdate,
    Resolver,
)


def test_create(
    test_db: Session,
    test_reference: Reference,
    test_feature: Feature,
    test_resolver: Resolver,
):
    """Test creating a referent."""
    # Create a referent using the create model with all required fields
    referent_create = ReferentCreate(
        reference_id=test_reference.id,
        feature_id=test_feature.id,
        resolver_id=test_resolver.id,
    )

    # Create the referent
    created_referent = ReferentRepository.create(test_db, referent_create)

    assert created_referent.id is not None
    assert created_referent.reference_id == test_reference.id
    assert created_referent.feature_id == test_feature.id

    # Verify it was saved to the database
    db_referent = test_db.get(Referent, created_referent.id)
    assert db_referent is not None
    assert db_referent.reference_id == test_reference.id
    assert db_referent.feature_id == test_feature.id


def test_get(test_db: Session, test_referent: Referent):
    """Test getting a referent by ID."""
    # Test with valid ID
    referent = ReferentRepository.get(test_db, test_referent.id)
    assert referent is not None
    assert referent.id == test_referent.id
    assert referent.reference_id == test_referent.reference_id
    assert referent.feature_id == test_referent.feature_id

    # Test with invalid ID
    invalid_id = uuid.uuid4()
    referent = ReferentRepository.get(test_db, invalid_id)
    assert referent is None


def test_get_by_reference(
    test_db: Session, test_reference: Reference, test_referent: Referent
):
    """Test getting referents by reference ID."""
    # Create another feature
    feature_create = FeatureCreate(
        gazetteer_name="another-gazetteer",
        table_name="another_table",
        identifier_name="another_id",
        identifier_value="654321",
    )
    another_feature = FeatureRepository.create(test_db, feature_create)

    # Create another referent for the same reference
    referent_create = ReferentCreate(
        reference_id=test_reference.id,
        feature_id=another_feature.id,
        resolver_id=test_referent.resolver_id,
    )

    # Create the referent
    ReferentRepository.create(test_db, referent_create)

    # Get referents by reference
    referents = ReferentRepository.get_by_reference(test_db, test_reference.id)
    assert len(referents) == 2
    assert any(r.feature_id == test_referent.feature_id for r in referents)
    assert any(r.feature_id == another_feature.id for r in referents)

    # Test with invalid reference ID
    invalid_id = uuid.uuid4()
    referents = ReferentRepository.get_by_reference(test_db, invalid_id)
    assert len(referents) == 0


def test_get_all(test_db: Session, test_referent: Referent):
    """Test getting all referents."""
    # Create another feature
    feature_create = FeatureCreate(
        gazetteer_name="another-gazetteer",
        table_name="another_table",
        identifier_name="another_id",
        identifier_value="654321",
    )
    another_feature = FeatureRepository.create(test_db, feature_create)

    # Create another referent
    referent_create = ReferentCreate(
        reference_id=test_referent.reference_id,
        feature_id=another_feature.id,
        resolver_id=test_referent.resolver_id,
    )

    # Create the referent
    ReferentRepository.create(test_db, referent_create)

    # Get all referents
    referents = ReferentRepository.get_all(test_db)
    assert len(referents) == 2
    assert any(r.feature_id == test_referent.feature_id for r in referents)
    assert any(r.feature_id == another_feature.id for r in referents)


def test_update(test_db: Session, test_referent: Referent):
    """Test updating a referent."""
    # Create a new feature to update to
    feature_create = FeatureCreate(
        gazetteer_name="updated-gazetteer",
        table_name="updated_table",
        identifier_name="updated_id",
        identifier_value="updated-value",
    )
    updated_feature = FeatureRepository.create(test_db, feature_create)

    # Update the referent
    referent_update = ReferentUpdate(id=test_referent.id, feature_id=updated_feature.id)
    updated_referent = ReferentRepository.update(
        test_db, db_obj=test_referent, obj_in=referent_update
    )

    assert updated_referent.id == test_referent.id
    assert updated_referent.feature_id == updated_feature.id

    # Verify it was updated in the database
    db_referent = test_db.get(Referent, test_referent.id)
    assert db_referent is not None
    assert db_referent.feature_id == updated_feature.id


def test_delete(test_db: Session, test_referent: Referent):
    """Test deleting a referent."""
    # Delete the referent
    deleted_referent = ReferentRepository.delete(test_db, id=test_referent.id)

    assert deleted_referent is not None
    assert deleted_referent.id == test_referent.id

    # Verify it was deleted from the database
    db_referent = test_db.get(Referent, test_referent.id)
    assert db_referent is None
