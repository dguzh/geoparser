import uuid

from sqlmodel import Session

from geoparser.db.crud import (
    DocumentRepository,
    ReferenceRepository,
    ResolutionRepository,
)
from geoparser.db.models import (
    Document,
    DocumentCreate,
    Reference,
    ReferenceCreate,
    Resolution,
    ResolutionCreate,
    ResolutionUpdate,
    Resolver,
    ResolverCreate,
)


def test_create(
    test_db: Session,
    test_reference: Reference,
    test_resolver: Resolver,
):
    """Test creating a resolution."""
    # Create a resolution using the create model with all required fields
    resolution_create = ResolutionCreate(
        resolver_id=test_resolver.id, reference_id=test_reference.id
    )

    # Create the resolution
    created_resolution = ResolutionRepository.create(test_db, resolution_create)

    assert created_resolution.id is not None
    assert created_resolution.reference_id == test_reference.id
    assert created_resolution.resolver_id == test_resolver.id

    # Verify it was saved to the database
    db_resolution = test_db.get(Resolution, created_resolution.id)
    assert db_resolution is not None
    assert db_resolution.reference_id == test_reference.id
    assert db_resolution.resolver_id == test_resolver.id


def test_get(test_db: Session, test_resolution: Resolution):
    """Test getting a resolution by ID."""
    # Test with valid ID
    resolution = ResolutionRepository.get(test_db, test_resolution.id)
    assert resolution is not None
    assert resolution.id == test_resolution.id
    assert resolution.reference_id == test_resolution.reference_id
    assert resolution.resolver_id == test_resolution.resolver_id

    # Test with invalid ID
    invalid_id = uuid.uuid4()
    resolution = ResolutionRepository.get(test_db, invalid_id)
    assert resolution is None


def test_get_by_reference(
    test_db: Session,
    test_reference: Reference,
    test_resolution: Resolution,
    test_resolver: Resolver,
):
    """Test getting resolutions by reference ID."""
    # Create another resolution module
    config = {"gazetteer": "test-gazetteer"}
    module_create = ResolverCreate(
        id="test-id", name="another-resolution-module", config=config
    )
    module = Resolver(
        id="auto-id", name=module_create.name, config=module_create.config
    )
    test_db.add(module)
    test_db.commit()
    test_db.refresh(module)

    # Create another resolution for the same reference
    resolution_create = ResolutionCreate(
        resolver_id=module.id, reference_id=test_reference.id
    )

    # Create the resolution
    ResolutionRepository.create(test_db, resolution_create)

    # Get resolutions by reference
    resolutions = ResolutionRepository.get_by_reference(test_db, test_reference.id)
    assert len(resolutions) == 2
    assert any(r.resolver_id == test_resolver.id for r in resolutions)
    assert any(r.resolver_id == module.id for r in resolutions)

    # Test with invalid reference ID
    invalid_id = uuid.uuid4()
    resolutions = ResolutionRepository.get_by_reference(test_db, invalid_id)
    assert len(resolutions) == 0


def test_get_by_resolver(
    test_db: Session,
    test_resolution: Resolution,
    test_resolver: Resolver,
):
    """Test getting resolutions by resolver ID."""
    # Create another reference
    reference_create = ReferenceCreate(
        start=10,
        end=14,
        document_id=test_resolution.reference.document_id,
        recognizer_id=test_resolution.reference.recognizer_id,
    )

    # Create the reference
    reference = ReferenceRepository.create(test_db, reference_create)

    # Create another resolution for the same module
    resolution_create = ResolutionCreate(
        resolver_id=test_resolver.id, reference_id=reference.id
    )

    # Create the resolution
    ResolutionRepository.create(test_db, resolution_create)

    # Get resolutions by resolver
    resolutions = ResolutionRepository.get_by_resolver(test_db, test_resolver.id)
    assert len(resolutions) == 2

    # Test with invalid resolver ID
    invalid_id = uuid.uuid4()
    resolutions = ResolutionRepository.get_by_resolver(test_db, invalid_id)
    assert len(resolutions) == 0


def test_get_all(test_db: Session, test_resolution: Resolution):
    """Test getting all resolutions."""
    # Create another resolution
    resolution_create = ResolutionCreate(
        resolver_id=test_resolution.resolver_id,
        reference_id=test_resolution.reference_id,
    )

    # Create the resolution
    ResolutionRepository.create(test_db, resolution_create)

    # Get all resolutions
    resolutions = ResolutionRepository.get_all(test_db)
    assert len(resolutions) >= 2


def test_update(test_db: Session, test_resolution: Resolution):
    """Test updating a resolution."""
    # Create a new module
    config = {"gazetteer": "updated-gazetteer"}
    module_create = ResolverCreate(id="test-id", name="updated-module", config=config)
    module = Resolver(
        id="auto-id", name=module_create.name, config=module_create.config
    )
    test_db.add(module)
    test_db.commit()
    test_db.refresh(module)

    # Update the resolution
    resolution_update = ResolutionUpdate(id=test_resolution.id, resolver_id=module.id)
    updated_resolution = ResolutionRepository.update(
        test_db, db_obj=test_resolution, obj_in=resolution_update
    )

    assert updated_resolution.id == test_resolution.id
    assert updated_resolution.resolver_id == module.id

    # Verify it was updated in the database
    db_resolution = test_db.get(Resolution, test_resolution.id)
    assert db_resolution is not None
    assert db_resolution.resolver_id == module.id


def test_delete(test_db: Session, test_resolution: Resolution):
    """Test deleting a resolution."""
    # Delete the resolution
    deleted_resolution = ResolutionRepository.delete(test_db, id=test_resolution.id)

    assert deleted_resolution is not None
    assert deleted_resolution.id == test_resolution.id

    # Verify it was deleted from the database
    db_resolution = test_db.get(Resolution, test_resolution.id)
    assert db_resolution is None


def test_get_by_reference_and_resolver(
    test_db: Session,
    test_reference: Reference,
    test_resolver: Resolver,
    test_resolution: Resolution,
):
    """Test getting a resolution by reference and resolver."""
    # Test with valid IDs
    resolution = ResolutionRepository.get_by_reference_and_resolver(
        test_db, test_reference.id, test_resolver.id
    )
    assert resolution is not None
    assert resolution.reference_id == test_reference.id
    assert resolution.resolver_id == test_resolver.id

    # Test with invalid IDs
    invalid_id = uuid.uuid4()
    resolution = ResolutionRepository.get_by_reference_and_resolver(
        test_db, invalid_id, test_resolver.id
    )
    assert resolution is None

    resolution = ResolutionRepository.get_by_reference_and_resolver(
        test_db, test_reference.id, invalid_id
    )
    assert resolution is None


def test_get_unprocessed_references(
    test_db: Session,
    test_document: Document,
    test_reference: Reference,
    test_resolver: Resolver,
    test_resolution: Resolution,
):
    """Test getting unprocessed references from a project."""
    # Create another document in the same project
    doc_create = DocumentCreate(
        text="Another test document with Berlin and Paris.",
        project_id=test_document.project_id,
    )
    another_document = DocumentRepository.create(test_db, doc_create)

    # Create references for the new document
    reference_create1 = ReferenceCreate(
        start=27,
        end=33,
        document_id=another_document.id,
        recognizer_id=test_reference.recognizer_id,  # "Berlin"
    )
    new_reference1 = ReferenceRepository.create(test_db, reference_create1)

    reference_create2 = ReferenceCreate(
        start=38,
        end=43,
        document_id=another_document.id,
        recognizer_id=test_reference.recognizer_id,  # "Paris"
    )
    new_reference2 = ReferenceRepository.create(test_db, reference_create2)

    # Process one of the new references with a different module
    config = {"gazetteer": "different-gazetteer"}
    new_module_create = ResolverCreate(
        id="test-id", name="different-resolution-module", config=config
    )
    new_module = Resolver(
        id="auto-id", name=new_module_create.name, config=new_module_create.config
    )
    test_db.add(new_module)
    test_db.commit()
    test_db.refresh(new_module)

    resolution_create = ResolutionCreate(
        resolver_id=new_module.id, reference_id=new_reference1.id
    )
    ResolutionRepository.create(test_db, resolution_create)

    # Get unprocessed references for test_resolver
    unprocessed_references = ResolutionRepository.get_unprocessed_references(
        test_db, test_document.project_id, test_resolver.id
    )

    # Should return new_reference1 and new_reference2 (not processed by test_resolver)
    assert len(unprocessed_references) == 2
    reference_ids = [reference.id for reference in unprocessed_references]
    assert new_reference1.id in reference_ids
    assert new_reference2.id in reference_ids
    assert test_reference.id not in reference_ids  # Already processed by test_resolver

    # Get unprocessed references for new_module
    unprocessed_references = ResolutionRepository.get_unprocessed_references(
        test_db, test_document.project_id, new_module.id
    )

    # Should return test_reference and new_reference2 (not processed by new_module)
    assert len(unprocessed_references) == 2
    reference_ids = [reference.id for reference in unprocessed_references]
    assert test_reference.id in reference_ids
    assert new_reference2.id in reference_ids
    assert new_reference1.id not in reference_ids  # Already processed by new_module

    # Test with non-existent project ID
    unprocessed_references = ResolutionRepository.get_unprocessed_references(
        test_db, uuid.uuid4(), test_resolver.id
    )
    assert len(unprocessed_references) == 0
