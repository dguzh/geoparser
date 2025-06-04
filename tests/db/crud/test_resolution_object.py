import uuid

from sqlmodel import Session

from geoparser.db.crud import (
    FeatureRepository,
    ReferentRepository,
    ResolutionObjectRepository,
)
from geoparser.db.models import (
    FeatureCreate,
    Referent,
    ReferentCreate,
    ResolutionModule,
    ResolutionModuleCreate,
    ResolutionObject,
    ResolutionObjectCreate,
    ResolutionObjectUpdate,
)


def test_create(
    test_db: Session,
    test_referent: Referent,
    test_resolution_module: ResolutionModule,
):
    """Test creating a resolution object."""
    # Create a resolution object using the create model with all required fields
    resolution_create = ResolutionObjectCreate(
        module_id=test_resolution_module.id, referent_id=test_referent.id
    )

    # Create the resolution object
    created_resolution = ResolutionObjectRepository.create(test_db, resolution_create)

    assert created_resolution.id is not None
    assert created_resolution.referent_id == test_referent.id
    assert created_resolution.module_id == test_resolution_module.id

    # Verify it was saved to the database
    db_resolution = test_db.get(ResolutionObject, created_resolution.id)
    assert db_resolution is not None
    assert db_resolution.referent_id == test_referent.id
    assert db_resolution.module_id == test_resolution_module.id


def test_get(test_db: Session, test_resolution_object: ResolutionObject):
    """Test getting a resolution object by ID."""
    # Test with valid ID
    resolution = ResolutionObjectRepository.get(test_db, test_resolution_object.id)
    assert resolution is not None
    assert resolution.id == test_resolution_object.id
    assert resolution.referent_id == test_resolution_object.referent_id
    assert resolution.module_id == test_resolution_object.module_id

    # Test with invalid ID
    invalid_id = uuid.uuid4()
    resolution = ResolutionObjectRepository.get(test_db, invalid_id)
    assert resolution is None


def test_get_by_referent(
    test_db: Session,
    test_referent: Referent,
    test_resolution_object: ResolutionObject,
    test_resolution_module: ResolutionModule,
):
    """Test getting resolution objects by referent ID."""
    # Create another resolution module
    config = {"gazetteer": "test-gazetteer"}
    module_create = ResolutionModuleCreate(
        name="another-resolution-module", config=config
    )
    module = ResolutionModule(name=module_create.name, config=module_create.config)
    test_db.add(module)
    test_db.commit()
    test_db.refresh(module)

    # Create another resolution object for the same referent
    resolution_create = ResolutionObjectCreate(
        module_id=module.id, referent_id=test_referent.id
    )

    # Create the resolution object
    ResolutionObjectRepository.create(test_db, resolution_create)

    # Get resolution objects by referent
    resolutions = ResolutionObjectRepository.get_by_referent(test_db, test_referent.id)
    assert len(resolutions) == 2
    assert any(r.module_id == test_resolution_module.id for r in resolutions)
    assert any(r.module_id == module.id for r in resolutions)

    # Test with invalid referent ID
    invalid_id = uuid.uuid4()
    resolutions = ResolutionObjectRepository.get_by_referent(test_db, invalid_id)
    assert len(resolutions) == 0


def test_get_by_module(
    test_db: Session,
    test_resolution_object: ResolutionObject,
    test_resolution_module: ResolutionModule,
):
    """Test getting resolution objects by module ID."""
    # Create another feature
    feature_create = FeatureCreate(
        gazetteer_name="another-gazetteer",
        table_name="another_table",
        identifier_name="another_id",
        identifier_value="another-referent",
    )
    another_feature = FeatureRepository.create(test_db, feature_create)

    # Create another referent
    referent_create = ReferentCreate(
        reference_id=test_resolution_object.referent.reference_id,
        feature_id=another_feature.id,
    )

    # Create the referent
    referent = ReferentRepository.create(test_db, referent_create)

    # Create another resolution object for the same module
    resolution_create = ResolutionObjectCreate(
        module_id=test_resolution_module.id, referent_id=referent.id
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


def test_get_all(test_db: Session, test_resolution_object: ResolutionObject):
    """Test getting all resolution objects."""
    # Create another resolution object
    resolution_create = ResolutionObjectCreate(
        module_id=test_resolution_object.module_id,
        referent_id=test_resolution_object.referent_id,
    )

    # Create the resolution object
    ResolutionObjectRepository.create(test_db, resolution_create)

    # Get all resolution objects
    resolutions = ResolutionObjectRepository.get_all(test_db)
    assert len(resolutions) >= 2


def test_update(test_db: Session, test_resolution_object: ResolutionObject):
    """Test updating a resolution object."""
    # Create a new module
    config = {"gazetteer": "updated-gazetteer"}
    module_create = ResolutionModuleCreate(name="updated-module", config=config)
    module = ResolutionModule(name=module_create.name, config=module_create.config)
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


def test_delete(test_db: Session, test_resolution_object: ResolutionObject):
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
