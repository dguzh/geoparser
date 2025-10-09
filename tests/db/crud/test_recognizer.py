from sqlmodel import Session

from geoparser.db.crud import RecognizerRepository
from geoparser.db.models import Recognizer, RecognizerCreate, RecognizerUpdate


def test_create(test_db: Session):
    """Test creating a recognizer."""
    config = {
        "model": "en_core_web_sm",
        "threshold": 0.8,
    }

    recognizer_create = RecognizerCreate(
        id="test-id", name="test-recognizer", config=config
    )
    recognizer = Recognizer(
        id="test-recognizer-1",
        name=recognizer_create.name,
        config=recognizer_create.config,
    )

    created_recognizer = RecognizerRepository.create(test_db, recognizer)

    assert created_recognizer.id is not None
    assert created_recognizer.name == "test-recognizer"
    assert created_recognizer.config == config

    # Verify it was saved to the database
    db_recognizer = test_db.get(Recognizer, created_recognizer.id)
    assert db_recognizer is not None
    assert db_recognizer.name == "test-recognizer"
    assert db_recognizer.config == config


def test_get(test_db: Session, test_recognizer: Recognizer):
    """Test getting a recognizer by ID."""
    # Test with valid ID
    recognizer = RecognizerRepository.get(test_db, test_recognizer.id)
    assert recognizer is not None
    assert recognizer.id == test_recognizer.id
    assert recognizer.name == test_recognizer.name
    assert recognizer.config == test_recognizer.config

    # Test with invalid ID
    invalid_id = "invalid-recognizer-id"
    recognizer = RecognizerRepository.get(test_db, invalid_id)
    assert recognizer is None


def test_get_by_name_and_config(test_db: Session):
    """Test getting a recognizer by name and config."""
    # Create recognizers with the same name but different configs
    config1 = {
        "model": "en_core_web_sm",
        "threshold": 0.8,
    }

    config2 = {
        "model": "en_core_web_lg",
        "threshold": 0.7,
    }

    recognizer_create1 = RecognizerCreate(
        id="test-id", name="same-name-recognizer", config=config1
    )
    recognizer1 = Recognizer(
        id="test-recognizer-2",
        name=recognizer_create1.name,
        config=recognizer_create1.config,
    )
    test_db.add(recognizer1)

    recognizer_create2 = RecognizerCreate(
        id="test-id", name="same-name-recognizer", config=config2
    )
    recognizer2 = Recognizer(
        id="test-recognizer-3",
        name=recognizer_create2.name,
        config=recognizer_create2.config,
    )
    test_db.add(recognizer2)

    test_db.commit()
    test_db.refresh(recognizer1)
    test_db.refresh(recognizer2)

    # Test with valid name and config
    retrieved_recognizer = RecognizerRepository.get_by_name_and_config(
        test_db, "same-name-recognizer", config1
    )
    assert retrieved_recognizer is not None
    assert retrieved_recognizer.id == recognizer1.id
    assert retrieved_recognizer.name == "same-name-recognizer"
    assert retrieved_recognizer.config == config1

    # Test with different config
    retrieved_recognizer = RecognizerRepository.get_by_name_and_config(
        test_db, "same-name-recognizer", config2
    )
    assert retrieved_recognizer is not None
    assert retrieved_recognizer.id == recognizer2.id
    assert retrieved_recognizer.name == "same-name-recognizer"
    assert retrieved_recognizer.config == config2

    # Test with non-existent config
    non_existent_config = {
        "model": "non_existent_model",
        "threshold": 0.5,
    }
    retrieved_recognizer = RecognizerRepository.get_by_name_and_config(
        test_db, "same-name-recognizer", non_existent_config
    )
    assert retrieved_recognizer is None

    # Test with non-existent name
    retrieved_recognizer = RecognizerRepository.get_by_name_and_config(
        test_db, "non-existent-recognizer", config1
    )
    assert retrieved_recognizer is None


def test_get_all(test_db: Session, test_recognizer: Recognizer):
    """Test getting all recognizers."""
    # Create another recognizer
    config = {"model": "en_core_web_md"}

    recognizer_create = RecognizerCreate(
        id="test-id", name="another-recognizer", config=config
    )
    recognizer = Recognizer(
        id="test-recognizer-4",
        name=recognizer_create.name,
        config=recognizer_create.config,
    )
    test_db.add(recognizer)
    test_db.commit()

    # Get all recognizers
    recognizers = RecognizerRepository.get_all(test_db)
    assert len(recognizers) >= 2
    assert any(r.name == test_recognizer.name for r in recognizers)
    assert any(r.name == "another-recognizer" for r in recognizers)


def test_update(test_db: Session, test_recognizer: Recognizer):
    """Test updating a recognizer."""
    # Update the recognizer
    updated_config = {
        "model": "updated-model",
        "threshold": 0.9,
    }

    recognizer_update = RecognizerUpdate(
        id=test_recognizer.id,
        name="updated-recognizer",
        config=updated_config,
    )
    updated_recognizer = RecognizerRepository.update(
        test_db, db_obj=test_recognizer, obj_in=recognizer_update
    )

    assert updated_recognizer.id == test_recognizer.id
    assert updated_recognizer.name == "updated-recognizer"
    assert updated_recognizer.config == updated_config

    # Verify it was updated in the database
    db_recognizer = test_db.get(Recognizer, test_recognizer.id)
    assert db_recognizer is not None
    assert db_recognizer.name == "updated-recognizer"
    assert db_recognizer.config == updated_config


def test_delete(test_db: Session, test_recognizer: Recognizer):
    """Test deleting a recognizer."""
    # Create a new recognizer to delete
    config = {"model": "to-be-deleted"}

    recognizer_create = RecognizerCreate(
        id="test-id", name="recognizer-to-delete", config=config
    )
    recognizer = Recognizer(
        id="test-recognizer-5",
        name=recognizer_create.name,
        config=recognizer_create.config,
    )
    test_db.add(recognizer)
    test_db.commit()
    test_db.refresh(recognizer)

    # Delete the recognizer
    deleted_recognizer = RecognizerRepository.delete(test_db, id=recognizer.id)

    assert deleted_recognizer is not None
    assert deleted_recognizer.id == recognizer.id
    assert deleted_recognizer.name == "recognizer-to-delete"
    assert deleted_recognizer.config == config

    # Verify it was deleted from the database
    db_recognizer = test_db.get(Recognizer, recognizer.id)
    assert db_recognizer is None
