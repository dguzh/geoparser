"""
Unit tests for geoparser/gazetteer/installer/stages/registration.py

Tests the RegistrationStage class.
"""

import pytest

from geoparser.gazetteer.installer.stages.registration import RegistrationStage


@pytest.mark.unit
class TestRegistrationStageInit:
    """Test RegistrationStage initialization."""

    def test_stores_gazetteer_name(self):
        """Test that gazetteer name is stored."""
        # Act
        stage = RegistrationStage("test_gazetteer")

        # Assert
        assert stage.gazetteer_name == "test_gazetteer"

    def test_initializes_feature_registration_builder(self):
        """Test that FeatureRegistrationBuilder is initialized."""
        # Act
        stage = RegistrationStage("test_gaz")

        # Assert
        assert stage.builder is not None
        assert hasattr(stage.builder, "build_feature_insert")

    def test_sets_name_and_description(self):
        """Test that stage name and description are set."""
        # Act
        stage = RegistrationStage("test_gaz")

        # Assert
        assert stage.name == "Registration"
        assert stage.description == "Register features and names"
