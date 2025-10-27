"""
Unit tests for geoparser/gazetteer/installer/stages/transformation.py

Tests the TransformationStage class.
"""

from unittest.mock import Mock, patch

import pytest

from geoparser.gazetteer.installer.model import (
    AttributesConfig,
    DataType,
    DerivedAttributeConfig,
    OriginalAttributeConfig,
    SourceConfig,
    SourceType,
)
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


@pytest.mark.unit
class TestTransformationStageBuildGeometries:
    """Test TransformationStage._build_geometries() error handling."""

    def test_raises_runtime_error_on_database_error(self):
        """Test that RuntimeError is raised when geometry building fails."""
        # Arrange
        import sqlalchemy as sa

        source = SourceConfig(
            name="test_source",
            path="/test/data.csv",
            file="data.csv",
            type=SourceType.TABULAR,
            separator=",",
            attributes=AttributesConfig(
                original=[
                    OriginalAttributeConfig(name="x", type=DataType.REAL),
                    OriginalAttributeConfig(name="y", type=DataType.REAL),
                    OriginalAttributeConfig(
                        name="geometry", type=DataType.GEOMETRY, srid=4326
                    ),
                ]
            ),
        )

        stage = TransformationStage()
        context = {"table_name": "test_table"}

        # Mock get_connection to raise a database error
        mock_connection = Mock()
        mock_connection.execute.side_effect = sa.exc.DatabaseError(
            "statement", {}, Exception("DB error")
        )
        mock_connection.__enter__ = Mock(return_value=mock_connection)
        mock_connection.__exit__ = Mock(return_value=None)

        # Act & Assert
        with patch(
            "geoparser.gazetteer.installer.stages.transformation.get_connection",
            return_value=mock_connection,
        ):
            with pytest.raises(RuntimeError, match="Failed to build geometry column"):
                stage._build_geometries(source, context["table_name"])

    def test_skips_when_no_geometry_attribute(self):
        """Test that geometry building is skipped when there's no geometry attribute."""
        # Arrange
        source = SourceConfig(
            name="test_source",
            path="/test/data.csv",
            file="data.csv",
            type=SourceType.TABULAR,
            separator=",",
            attributes=AttributesConfig(
                original=[
                    OriginalAttributeConfig(name="id", type=DataType.INTEGER),
                    OriginalAttributeConfig(name="name", type=DataType.TEXT),
                ]
            ),
        )

        stage = TransformationStage()

        # Mock get_connection
        mock_get_connection = Mock()

        # Act - This should not raise an error or call get_connection
        with patch(
            "geoparser.gazetteer.installer.stages.transformation.get_connection",
            mock_get_connection,
        ):
            stage._build_geometries(source, "test_table")

        # Assert - get_connection should not have been called because there's no geometry
        mock_get_connection.assert_not_called()


@pytest.mark.unit
class TestTransformationStageFindGeometryAttribute:
    """Test TransformationStage._find_geometry_attribute() method."""

    def test_returns_none_when_no_geometry_in_original_or_derived(self):
        """Test that None is returned when there's no geometry attribute."""
        # Arrange
        source = SourceConfig(
            name="test_source",
            path="/test/data.csv",
            file="data.csv",
            type=SourceType.TABULAR,
            separator=",",
            attributes=AttributesConfig(
                original=[
                    OriginalAttributeConfig(name="id", type=DataType.INTEGER),
                    OriginalAttributeConfig(name="name", type=DataType.TEXT),
                ]
            ),
        )

        stage = TransformationStage()

        # Act
        result = stage._find_geometry_attribute(source)

        # Assert
        assert result is None

    def test_finds_geometry_in_derived_attributes(self):
        """Test that geometry attribute is found in derived attributes."""
        # Arrange
        source = SourceConfig(
            name="test_source",
            path="/test/data.csv",
            file="data.csv",
            type=SourceType.TABULAR,
            separator=",",
            attributes=AttributesConfig(
                original=[
                    OriginalAttributeConfig(name="x", type=DataType.REAL),
                    OriginalAttributeConfig(name="y", type=DataType.REAL),
                ],
                derived=[
                    DerivedAttributeConfig(
                        name="geometry",
                        type=DataType.GEOMETRY,
                        expression="MakePoint(x, y)",
                        srid=4326,
                    )
                ],
            ),
        )

        stage = TransformationStage()

        # Act
        result = stage._find_geometry_attribute(source)

        # Assert
        assert result is not None
        assert result.name == "geometry"
        assert result.type == DataType.GEOMETRY
