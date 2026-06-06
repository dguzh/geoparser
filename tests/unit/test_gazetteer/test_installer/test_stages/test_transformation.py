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
class TestTransformationStageInit:
    """Test TransformationStage initialization."""

    def test_initializes_transformation_builder(self):
        """Test that TransformationBuilder is initialized."""
        # Act
        stage = TransformationStage()

        # Assert
        assert stage.transformation_builder is not None
        assert hasattr(stage.transformation_builder, "build_derivation_update")

    def test_sets_name_and_description(self):
        """Test that stage name and description are set."""
        # Act
        stage = TransformationStage()

        # Assert
        assert stage.name == "Transformation"
        assert stage.description == "Apply derivations"


@pytest.mark.unit
class TestTransformationStageApplyDerivations:
    """Test TransformationStage._apply_derivations() method."""

    def test_skips_when_no_derived_attributes(self):
        """Test that derivations are skipped when there are none."""
        # Arrange
        source = SourceConfig(
            name="test_source",
            path="/test/data.csv",
            file="data.csv",
            type=SourceType.TABULAR,
            separator=",",
            attributes=AttributesConfig(
                original=[OriginalAttributeConfig(name="id", type=DataType.INTEGER)]
            ),
        )

        stage = TransformationStage()
        mock_get_connection = Mock()

        # Act
        with patch(
            "geoparser.gazetteer.installer.stages.transformation.get_connection",
            mock_get_connection,
        ):
            stage._apply_derivations(source, "test_table")

        # Assert
        mock_get_connection.assert_not_called()

    def test_derives_geometry_into_geometry_column(self):
        """Test that geometry derivations target the geometry column directly."""
        # Arrange
        source = SourceConfig(
            name="test_source",
            path="/test/data.csv",
            file="data.csv",
            type=SourceType.TABULAR,
            separator=",",
            attributes=AttributesConfig(
                original=[
                    OriginalAttributeConfig(name="lon", type=DataType.REAL),
                    OriginalAttributeConfig(name="lat", type=DataType.REAL),
                ],
                derived=[
                    DerivedAttributeConfig(
                        name="geometry",
                        type=DataType.GEOMETRY,
                        expression="'POINT(' || lon || ' ' || lat || ')'",
                        srid=4326,
                    )
                ],
            ),
        )

        stage = TransformationStage()

        executed = []
        mock_connection = Mock()
        mock_connection.execute = lambda stmt: executed.append(str(stmt))
        mock_connection.commit = Mock()
        mock_connection.__enter__ = Mock(return_value=mock_connection)
        mock_connection.__exit__ = Mock(return_value=None)

        # Act
        with patch(
            "geoparser.gazetteer.installer.stages.transformation.get_connection",
            return_value=mock_connection,
        ):
            stage._apply_derivations(source, "test_table")

        # Assert - geometry derivation writes WKT into the 'geometry' column
        assert any("SET geometry = " in c for c in executed)
        assert all("GeomFromText" not in c for c in executed)
        assert all("geometry_wkt" not in c for c in executed)
