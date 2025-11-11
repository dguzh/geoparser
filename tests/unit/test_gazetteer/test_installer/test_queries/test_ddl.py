"""
Unit tests for geoparser/gazetteer/installer/queries/ddl.py

Tests the TableBuilder and ViewBuilder classes for DDL SQL generation.
"""

import pytest

from geoparser.gazetteer.installer.model import (
    AttributesConfig,
    DataType,
    DerivedAttributeConfig,
    OriginalAttributeConfig,
    SelectConfig,
    SourceConfig,
    SourceType,
    ViewConfig,
    ViewJoinConfig,
)
from geoparser.gazetteer.installer.queries.ddl import TableBuilder, ViewBuilder


@pytest.mark.unit
class TestTableBuilderBuildCreateTable:
    """Test TableBuilder.build_create_table() method."""

    def test_builds_table_with_single_column(self):
        """Test building CREATE TABLE with a single column."""
        # Arrange
        source = SourceConfig(
            name="test_source",
            url="http://example.com/data.csv",
            file="data.csv",
            type=SourceType.TABULAR,
            separator=",",
            attributes=AttributesConfig(
                original=[OriginalAttributeConfig(name="id", type=DataType.INTEGER)]
            ),
        )

        builder = TableBuilder()

        # Act
        sql = builder.build_create_table(source, "test_table")

        # Assert
        assert sql == "CREATE TABLE test_table (id INTEGER)"

    def test_builds_table_with_multiple_columns(self):
        """Test building CREATE TABLE with multiple columns."""
        # Arrange
        source = SourceConfig(
            name="test_source",
            url="http://example.com/data.csv",
            file="data.csv",
            type=SourceType.TABULAR,
            separator=",",
            attributes=AttributesConfig(
                original=[
                    OriginalAttributeConfig(name="id", type=DataType.INTEGER),
                    OriginalAttributeConfig(name="name", type=DataType.TEXT),
                    OriginalAttributeConfig(name="value", type=DataType.REAL),
                ]
            ),
        )

        builder = TableBuilder()

        # Act
        sql = builder.build_create_table(source, "test_table")

        # Assert
        assert sql == "CREATE TABLE test_table (id INTEGER, name TEXT, value REAL)"

    def test_excludes_dropped_columns(self):
        """Test that dropped columns are excluded from table creation."""
        # Arrange
        source = SourceConfig(
            name="test_source",
            url="http://example.com/data.csv",
            file="data.csv",
            type=SourceType.TABULAR,
            separator=",",
            attributes=AttributesConfig(
                original=[
                    OriginalAttributeConfig(name="id", type=DataType.INTEGER),
                    OriginalAttributeConfig(name="temp", type=DataType.TEXT, drop=True),
                    OriginalAttributeConfig(name="name", type=DataType.TEXT),
                ]
            ),
        )

        builder = TableBuilder()

        # Act
        sql = builder.build_create_table(source, "test_table")

        # Assert
        assert "temp" not in sql
        assert sql == "CREATE TABLE test_table (id INTEGER, name TEXT)"

    def test_creates_geometry_column_as_wkt_text(self):
        """Test that geometry columns are created as TEXT with _wkt suffix."""
        # Arrange
        source = SourceConfig(
            name="test_source",
            url="http://example.com/data.shp",
            file="data.shp",
            type=SourceType.SPATIAL,
            attributes=AttributesConfig(
                original=[
                    OriginalAttributeConfig(name="id", type=DataType.INTEGER),
                    OriginalAttributeConfig(
                        name="geometry", type=DataType.GEOMETRY, srid=4326
                    ),
                ]
            ),
        )

        builder = TableBuilder()

        # Act
        sql = builder.build_create_table(source, "test_table")

        # Assert
        assert sql == "CREATE TABLE test_table (id INTEGER, geometry_wkt TEXT)"

    def test_includes_derived_columns(self):
        """Test that derived columns are included in table creation."""
        # Arrange
        source = SourceConfig(
            name="test_source",
            url="http://example.com/data.csv",
            file="data.csv",
            type=SourceType.TABULAR,
            separator=",",
            attributes=AttributesConfig(
                original=[
                    OriginalAttributeConfig(name="first", type=DataType.TEXT),
                    OriginalAttributeConfig(name="last", type=DataType.TEXT),
                ],
                derived=[
                    DerivedAttributeConfig(
                        name="full_name",
                        type=DataType.TEXT,
                        expression="first || ' ' || last",
                    )
                ],
            ),
        )

        builder = TableBuilder()

        # Act
        sql = builder.build_create_table(source, "test_table")

        # Assert
        assert "full_name TEXT" in sql


@pytest.mark.unit
class TestTableBuilderBuildAddGeometryColumn:
    """Test TableBuilder.build_add_geometry_column() method."""

    def test_builds_add_geometry_column_with_defaults(self):
        """Test building AddGeometryColumn with default parameters."""
        # Arrange
        builder = TableBuilder()

        # Act
        sql = builder.build_add_geometry_column("test_table", "geometry", 4326)

        # Assert
        assert sql == (
            "SELECT AddGeometryColumn('test_table', 'geometry', 4326, 'GEOMETRY', 'XY')"
        )

    def test_builds_add_geometry_column_with_custom_type(self):
        """Test building AddGeometryColumn with custom geometry type."""
        # Arrange
        builder = TableBuilder()

        # Act
        sql = builder.build_add_geometry_column(
            "test_table", "geometry", 4326, geometry_type="POINT"
        )

        # Assert
        assert sql == (
            "SELECT AddGeometryColumn('test_table', 'geometry', 4326, 'POINT', 'XY')"
        )

    def test_builds_add_geometry_column_with_custom_dimension(self):
        """Test building AddGeometryColumn with custom dimension."""
        # Arrange
        builder = TableBuilder()

        # Act
        sql = builder.build_add_geometry_column(
            "test_table", "geometry", 4326, dimension="XYZ"
        )

        # Assert
        assert sql == (
            "SELECT AddGeometryColumn('test_table', 'geometry', 4326, 'GEOMETRY', 'XYZ')"
        )


@pytest.mark.unit
class TestViewBuilderBuildCreateView:
    """Test ViewBuilder.build_create_view() method."""

    def test_builds_view_with_simple_select(self):
        """Test building CREATE VIEW with simple select clause."""
        # Arrange
        source = SourceConfig(
            name="test_source",
            url="http://example.com/data.csv",
            file="data.csv",
            type=SourceType.TABULAR,
            separator=",",
            attributes=AttributesConfig(
                original=[OriginalAttributeConfig(name="id", type=DataType.INTEGER)]
            ),
            view=ViewConfig(select=[SelectConfig(source="test_source", column="id")]),
        )

        builder = ViewBuilder()

        # Act
        sql = builder.build_create_view(source, "test_view")

        # Assert
        assert sql == "CREATE VIEW test_view AS SELECT test_source.id FROM test_source"

    def test_builds_view_with_column_alias(self):
        """Test building CREATE VIEW with column alias."""
        # Arrange
        source = SourceConfig(
            name="test_source",
            url="http://example.com/data.csv",
            file="data.csv",
            type=SourceType.TABULAR,
            separator=",",
            attributes=AttributesConfig(
                original=[OriginalAttributeConfig(name="id", type=DataType.INTEGER)]
            ),
            view=ViewConfig(
                select=[
                    SelectConfig(source="test_source", column="id", alias="source_id")
                ]
            ),
        )

        builder = ViewBuilder()

        # Act
        sql = builder.build_create_view(source, "test_view")

        # Assert
        assert "test_source.id AS source_id" in sql

    def test_builds_view_with_multiple_columns(self):
        """Test building CREATE VIEW with multiple columns."""
        # Arrange
        source = SourceConfig(
            name="test_source",
            url="http://example.com/data.csv",
            file="data.csv",
            type=SourceType.TABULAR,
            separator=",",
            attributes=AttributesConfig(
                original=[
                    OriginalAttributeConfig(name="id", type=DataType.INTEGER),
                    OriginalAttributeConfig(name="name", type=DataType.TEXT),
                ]
            ),
            view=ViewConfig(
                select=[
                    SelectConfig(source="test_source", column="id"),
                    SelectConfig(source="test_source", column="name"),
                ]
            ),
        )

        builder = ViewBuilder()

        # Act
        sql = builder.build_create_view(source, "test_view")

        # Assert
        assert "test_source.id, test_source.name" in sql

    def test_builds_view_with_join(self):
        """Test building CREATE VIEW with join clause."""
        # Arrange
        source = SourceConfig(
            name="source2",
            url="http://example.com/data.csv",
            file="data.csv",
            type=SourceType.TABULAR,
            separator=",",
            attributes=AttributesConfig(
                original=[OriginalAttributeConfig(name="id", type=DataType.INTEGER)]
            ),
            view=ViewConfig(
                select=[SelectConfig(source="source2", column="id")],
                join=[
                    ViewJoinConfig(
                        type="LEFT JOIN",
                        source="source1",
                        condition="source2.id = source1.id",
                    )
                ],
            ),
        )

        builder = ViewBuilder()

        # Act
        sql = builder.build_create_view(source, "test_view")

        # Assert
        assert "LEFT JOIN source1 ON" in sql
        assert "source2.id = source1.id" in sql

    def test_raises_error_when_source_has_no_view(self):
        """Test that error is raised when source has no view configuration."""
        # Arrange
        source = SourceConfig(
            name="test_source",
            url="http://example.com/data.csv",
            file="data.csv",
            type=SourceType.TABULAR,
            separator=",",
            attributes=AttributesConfig(
                original=[OriginalAttributeConfig(name="id", type=DataType.INTEGER)]
            ),
        )

        builder = ViewBuilder()

        # Act & Assert
        with pytest.raises(ValueError, match="has no view configuration"):
            builder.build_create_view(source, "test_view")
