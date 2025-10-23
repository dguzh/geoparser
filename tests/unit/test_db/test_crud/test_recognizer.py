"""
Unit tests for geoparser/db/crud/recognizer.py

Tests the RecognizerRepository class with custom query methods.
"""

import pytest
from sqlmodel import Session

from geoparser.db.crud import RecognizerRepository


@pytest.mark.unit
class TestRecognizerRepositoryGetByNameAndConfig:
    """Test the get_by_name_and_config method of RecognizerRepository."""

    def test_returns_recognizer_for_matching_name_and_config(
        self, test_session: Session, recognizer_factory
    ):
        """Test that get_by_name_and_config returns recognizer when both match."""
        # Arrange
        config = {"model": "en_core_web_sm", "threshold": 0.5}
        recognizer = recognizer_factory(name="SpacyRecognizer", config=config)

        # Act
        found_recognizer = RecognizerRepository.get_by_name_and_config(
            test_session, "SpacyRecognizer", config
        )

        # Assert
        assert found_recognizer is not None
        assert found_recognizer.id == recognizer.id
        assert found_recognizer.name == "SpacyRecognizer"
        assert found_recognizer.config == config

    def test_returns_none_for_non_matching_name(
        self, test_session: Session, recognizer_factory
    ):
        """Test that get_by_name_and_config returns None when name doesn't match."""
        # Arrange
        config = {"model": "en_core_web_sm"}
        recognizer = recognizer_factory(name="SpacyRecognizer", config=config)

        # Act
        found_recognizer = RecognizerRepository.get_by_name_and_config(
            test_session, "ManualRecognizer", config
        )

        # Assert
        assert found_recognizer is None

    def test_returns_none_for_non_matching_config(
        self, test_session: Session, recognizer_factory
    ):
        """Test that get_by_name_and_config returns None when config doesn't match."""
        # Arrange
        config1 = {"model": "en_core_web_sm"}
        config2 = {"model": "en_core_web_lg"}
        recognizer = recognizer_factory(name="SpacyRecognizer", config=config1)

        # Act
        found_recognizer = RecognizerRepository.get_by_name_and_config(
            test_session, "SpacyRecognizer", config2
        )

        # Assert
        assert found_recognizer is None

    def test_distinguishes_between_same_name_different_configs(
        self, test_session: Session, recognizer_factory
    ):
        """Test that method can distinguish recognizers with same name but different configs."""
        # Arrange
        config1 = {"model": "en_core_web_sm"}
        config2 = {"model": "en_core_web_lg"}

        rec1 = recognizer_factory(name="SpacyRecognizer", config=config1)
        rec2 = recognizer_factory(name="SpacyRecognizer", config=config2)

        # Act
        found_rec1 = RecognizerRepository.get_by_name_and_config(
            test_session, "SpacyRecognizer", config1
        )
        found_rec2 = RecognizerRepository.get_by_name_and_config(
            test_session, "SpacyRecognizer", config2
        )

        # Assert
        assert found_rec1 is not None
        assert found_rec2 is not None
        assert found_rec1.id == rec1.id
        assert found_rec2.id == rec2.id
        assert found_rec1.id != found_rec2.id
