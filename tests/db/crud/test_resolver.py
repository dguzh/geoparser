import uuid

from sqlmodel import Session

from geoparser.db.crud import ResolverRepository
from geoparser.db.models import Resolver, ResolverCreate, ResolverUpdate


def test_create(test_db: Session):
    """Test creating a resolver."""
    config = {
        "gazetteer": "test-gazetteer",
        "max_results": 5,
    }

    resolver_create = ResolverCreate(name="test-resolver", config=config)
    resolver = Resolver(name=resolver_create.name, config=resolver_create.config)

    created_resolver = ResolverRepository.create(test_db, resolver)

    assert created_resolver.id is not None
    assert created_resolver.name == "test-resolver"
    assert created_resolver.config == config

    # Verify it was saved to the database
    db_resolver = test_db.get(Resolver, created_resolver.id)
    assert db_resolver is not None
    assert db_resolver.name == "test-resolver"
    assert db_resolver.config == config


def test_get(test_db: Session, test_resolver: Resolver):
    """Test getting a resolver by ID."""
    # Test with valid ID
    resolver = ResolverRepository.get(test_db, test_resolver.id)
    assert resolver is not None
    assert resolver.id == test_resolver.id
    assert resolver.name == test_resolver.name
    assert resolver.config == test_resolver.config

    # Test with invalid ID
    invalid_id = uuid.uuid4()
    resolver = ResolverRepository.get(test_db, invalid_id)
    assert resolver is None


def test_get_by_name_and_config(test_db: Session):
    """Test getting a resolver by name and config."""
    # Create resolvers with the same name but different configs
    config1 = {
        "gazetteer": "gazetteer1",
        "max_results": 5,
    }

    config2 = {
        "gazetteer": "gazetteer2",
        "max_results": 10,
    }

    resolver_create1 = ResolverCreate(name="same-name-resolver", config=config1)
    resolver1 = Resolver(name=resolver_create1.name, config=resolver_create1.config)
    test_db.add(resolver1)

    resolver_create2 = ResolverCreate(name="same-name-resolver", config=config2)
    resolver2 = Resolver(name=resolver_create2.name, config=resolver_create2.config)
    test_db.add(resolver2)

    test_db.commit()
    test_db.refresh(resolver1)
    test_db.refresh(resolver2)

    # Test with valid name and config
    retrieved_resolver = ResolverRepository.get_by_name_and_config(
        test_db, "same-name-resolver", config1
    )
    assert retrieved_resolver is not None
    assert retrieved_resolver.id == resolver1.id
    assert retrieved_resolver.name == "same-name-resolver"
    assert retrieved_resolver.config == config1

    # Test with different config
    retrieved_resolver = ResolverRepository.get_by_name_and_config(
        test_db, "same-name-resolver", config2
    )
    assert retrieved_resolver is not None
    assert retrieved_resolver.id == resolver2.id
    assert retrieved_resolver.name == "same-name-resolver"
    assert retrieved_resolver.config == config2

    # Test with non-existent config
    non_existent_config = {
        "gazetteer": "non_existent_gazetteer",
        "max_results": 15,
    }
    retrieved_resolver = ResolverRepository.get_by_name_and_config(
        test_db, "same-name-resolver", non_existent_config
    )
    assert retrieved_resolver is None

    # Test with non-existent name
    retrieved_resolver = ResolverRepository.get_by_name_and_config(
        test_db, "non-existent-resolver", config1
    )
    assert retrieved_resolver is None


def test_get_all(test_db: Session, test_resolver: Resolver):
    """Test getting all resolvers."""
    # Create another module
    config = {
        "gazetteer": "another-gazetteer",
    }

    resolver_create = ResolverCreate(name="another-resolver", config=config)
    resolver = Resolver(name=resolver_create.name, config=resolver_create.config)
    test_db.add(resolver)
    test_db.commit()

    # Get all resolvers
    resolvers = ResolverRepository.get_all(test_db)
    assert len(resolvers) >= 2
    assert any(r.name == test_resolver.name for r in resolvers)
    assert any(r.name == "another-resolver" for r in resolvers)


def test_update(test_db: Session, test_resolver: Resolver):
    """Test updating a resolver."""
    # Update the module
    updated_config = {
        "gazetteer": "updated-gazetteer",
        "max_results": 20,
    }

    resolver_update = ResolverUpdate(
        id=test_resolver.id,
        name="updated-resolver",
        config=updated_config,
    )
    updated_resolver = ResolverRepository.update(
        test_db, db_obj=test_resolver, obj_in=resolver_update
    )

    assert updated_resolver.id == test_resolver.id
    assert updated_resolver.name == "updated-resolver"
    assert updated_resolver.config == updated_config

    # Verify it was updated in the database
    db_resolver = test_db.get(Resolver, test_resolver.id)
    assert db_resolver is not None
    assert db_resolver.name == "updated-resolver"
    assert db_resolver.config == updated_config


def test_delete(test_db: Session, test_resolver: Resolver):
    """Test deleting a resolver."""
    # Create a new resolver to delete
    config = {"gazetteer": "to-be-deleted"}

    resolver_create = ResolverCreate(name="resolver-to-delete", config=config)
    resolver = Resolver(name=resolver_create.name, config=resolver_create.config)
    test_db.add(resolver)
    test_db.commit()
    test_db.refresh(resolver)

    # Delete the resolver
    deleted_resolver = ResolverRepository.delete(test_db, id=resolver.id)

    assert deleted_resolver is not None
    assert deleted_resolver.id == resolver.id
    assert deleted_resolver.name == "resolver-to-delete"
    assert deleted_resolver.config == config

    # Verify it was deleted from the database
    db_resolver = test_db.get(Resolver, resolver.id)
    assert db_resolver is None
