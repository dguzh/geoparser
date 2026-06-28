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
    SourceKind,
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

    def test_initializes_with_default_chunksize(self):
        """Test that default chunksize is set."""
        # Act
        stage = TransformationStage()

        # Assert
        assert stage.chunksize == 100_000

    def test_initializes_with_custom_chunksize(self):
        """Test that custom chunksize is accepted."""
        # Act
        stage = TransformationStage(chunksize=5000)

        # Assert
        assert stage.chunksize == 5000


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
            kind=SourceKind.TABULAR,
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
            kind=SourceKind.TABULAR,
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
        ), patch(
            "geoparser.gazetteer.installer.stages.transformation.count_rows",
            return_value=3,
        ):
            stage._apply_derivations(source, "test_table")

        # Assert - geometry derivation writes WKT into the 'geometry' column
        assert any("SET geometry = " in c for c in executed)
        assert all("GeomFromText" not in c for c in executed)
        assert all("geometry_wkt" not in c for c in executed)

    def test_applies_derivation_in_chunks(self):
        """Test that derivations run in rowid-bounded chunks."""
        # Arrange
        source = SourceConfig(
            name="test_source",
            path="/test/data.csv",
            file="data.csv",
            kind=SourceKind.TABULAR,
            separator=",",
            attributes=AttributesConfig(
                original=[OriginalAttributeConfig(name="name", type=DataType.TEXT)],
                derived=[
                    DerivedAttributeConfig(
                        name="upper_name",
                        type=DataType.TEXT,
                        expression="upper(name)",
                    )
                ],
            ),
        )

        stage = TransformationStage(chunksize=2)

        executed = []
        mock_connection = Mock()
        mock_connection.execute = lambda stmt: executed.append(str(stmt))
        mock_connection.commit = Mock()
        mock_connection.__enter__ = Mock(return_value=mock_connection)
        mock_connection.__exit__ = Mock(return_value=None)

        # Act - 5 rows with chunksize 2 should produce 3 chunked updates
        with patch(
            "geoparser.gazetteer.installer.stages.transformation.get_connection",
            return_value=mock_connection,
        ), patch(
            "geoparser.gazetteer.installer.stages.transformation.count_rows",
            return_value=5,
        ):
            stage._apply_derivations(source, "test_table")

        # Assert - one update per chunk with the expected rowid bounds
        assert len(executed) == 3
        assert any("WHERE rowid BETWEEN 1 AND 2" in c for c in executed)
        assert any("WHERE rowid BETWEEN 3 AND 4" in c for c in executed)
        assert any("WHERE rowid BETWEEN 5 AND 5" in c for c in executed)
