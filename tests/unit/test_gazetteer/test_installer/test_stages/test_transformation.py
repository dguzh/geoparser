"""
Unit tests for geoparser/gazetteer/installer/stages/transformation.py

Tests the TransformationStage class.
"""

import pytest

from geoparser.gazetteer.installer.stages.transformation import TransformationStage


@pytest.mark.unit
class TestTransformationStageConstants:
    """Test TransformationStage constants."""

    def test_has_geometry_type_constant(self):
        """Test that GEOMETRY_TYPE constant is defined."""
        assert TransformationStage.GEOMETRY_TYPE == "GEOMETRY"

    def test_has_coordinate_dimension_constant(self):
        """Test that COORDINATE_DIMENSION constant is defined."""
        assert TransformationStage.COORDINATE_DIMENSION == "XY"


@pytest.mark.unit
class TestTransformationStageInit:
    """Test TransformationStage initialization."""

    def test_initializes_transformation_builder(self):
        """Test that TransformationBuilder is initialized."""
        # Act
        stage = TransformationStage()

        # Assert
        assert stage.transformation_builder is not None
        assert hasattr(stage.transformation_builder, "build_derivation_update")

    def test_initializes_table_builder(self):
        """Test that TableBuilder is initialized."""
        # Act
        stage = TransformationStage()

        # Assert
        assert stage.table_builder is not None
        assert hasattr(stage.table_builder, "build_add_geometry_column")

    def test_sets_name_and_description(self):
        """Test that stage name and description are set."""
        # Act
        stage = TransformationStage()

        # Assert
        assert stage.name == "Transformation"
        assert stage.description == "Apply derivations and build geometries"
