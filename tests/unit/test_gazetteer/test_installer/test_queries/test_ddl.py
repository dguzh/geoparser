"""
Unit tests for geoparser/gazetteer/installer/queries/ddl.py

Tests the TableBuilder and ViewBuilder classes for DDL SQL generation.
"""

import pytest

from geoparser.gazetteer.installer.model import (
    AttributeConditionConfig,
    AttributesConfig,
    DataType,
    DerivedAttributeConfig,
    JoinOperandConfig,
    OriginalAttributeConfig,
    SelectConfig,
    SourceConfig,
    SourceKind,
    SpatialConditionConfig,
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
            kind=SourceKind.TABULAR,
            separator=",",
            attributes=AttributesConfig(
                original=[OriginalAttributeConfig(name="id", type=DataType.INTEGER)]
            ),
        )

        builder = TableBuilder()

        # Act
        sql = builder.build_create_table(source, "test_table")

        # Assert
        assert sql == "CREATE TABLE test_table (id integer)"

    def test_builds_table_with_multiple_columns(self):
        """Test building CREATE TABLE with multiple columns."""
        # Arrange
        source = SourceConfig(
            name="test_source",
            url="http://example.com/data.csv",
            file="data.csv",
            kind=SourceKind.TABULAR,
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
        assert sql == "CREATE TABLE test_table (id integer, name text, value real)"

    def test_excludes_dropped_columns(self):
        """Test that dropped columns are excluded from table creation."""
        # Arrange
        source = SourceConfig(
            name="test_source",
            url="http://example.com/data.csv",
            file="data.csv",
            kind=SourceKind.TABULAR,
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
        assert sql == "CREATE TABLE test_table (id integer, name text)"

    def test_creates_geometry_column_as_wkt_text(self):
        """Test that geometry columns are created as TEXT (storing WKT)."""
        # Arrange
        source = SourceConfig(
            name="test_source",
            url="http://example.com/data.shp",
            file="data.shp",
            kind=SourceKind.SPATIAL,
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
        assert sql == "CREATE TABLE test_table (id integer, geometry text)"

    def test_includes_derived_columns(self):
        """Test that derived columns are included in table creation."""
        # Arrange
        source = SourceConfig(
            name="test_source",
            url="http://example.com/data.csv",
            file="data.csv",
            kind=SourceKind.TABULAR,
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
        assert "full_name text" in sql


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
            kind=SourceKind.TABULAR,
            separator=",",
            attributes=AttributesConfig(
                original=[OriginalAttributeConfig(name="id", type=DataType.INTEGER)]
            ),
            view=ViewConfig(select=[SelectConfig(column="test_source.id")]),
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
            kind=SourceKind.TABULAR,
            separator=",",
            attributes=AttributesConfig(
                original=[OriginalAttributeConfig(name="id", type=DataType.INTEGER)]
            ),
            view=ViewConfig(
                select=[SelectConfig(column="test_source.id", alias="source_id")]
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
            kind=SourceKind.TABULAR,
            separator=",",
            attributes=AttributesConfig(
                original=[
                    OriginalAttributeConfig(name="id", type=DataType.INTEGER),
                    OriginalAttributeConfig(name="name", type=DataType.TEXT),
                ]
            ),
            view=ViewConfig(
                select=[
                    SelectConfig(column="test_source.id"),
                    SelectConfig(column="test_source.name"),
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
            kind=SourceKind.TABULAR,
            separator=",",
            attributes=AttributesConfig(
                original=[OriginalAttributeConfig(name="id", type=DataType.INTEGER)]
            ),
            view=ViewConfig(
                select=[SelectConfig(column="source2.id")],
                join=[
                    ViewJoinConfig(
                        method="left join",
                        condition=AttributeConditionConfig(
                            predicate="equals",
                            left=JoinOperandConfig(column="source2.id"),
                            right=JoinOperandConfig(column="source1.id"),
                        ),
                    )
                ],
            ),
        )

        builder = ViewBuilder()

        # Act
        sql = builder.build_create_view(source, "test_view")

        # Assert
        assert "left join source1 ON" in sql
        assert "source2.id = source1.id" in sql

    def test_builds_view_with_spatial_join_as_equality(self):
        """Test that spatial joins are emitted as precomputed equality joins."""
        # Arrange
        source = SourceConfig(
            name="points",
            url="http://example.com/data.csv",
            file="data.csv",
            kind=SourceKind.TABULAR,
            separator=",",
            attributes=AttributesConfig(
                original=[OriginalAttributeConfig(name="id", type=DataType.INTEGER)],
                derived=[
                    DerivedAttributeConfig(
                        name="geometry",
                        type=DataType.GEOMETRY,
                        expression="'POINT(0 0)'",
                        srid=4326,
                    )
                ],
            ),
            view=ViewConfig(
                select=[SelectConfig(column="points.id")],
                join=[
                    ViewJoinConfig(
                        method="left join",
                        condition=SpatialConditionConfig(
                            predicate="within",
                            left=JoinOperandConfig(column="points.geometry"),
                            right=JoinOperandConfig(column="regions.geometry"),
                        ),
                    )
                ],
            ),
        )

        builder = ViewBuilder()

        # Act
        sql = builder.build_create_view(source, "test_view")

        # Assert
        assert "left join regions ON" in sql
        assert "points.__spatial_join_regions = regions.rowid" in sql
        assert "ST_Within" not in sql

    def test_raises_error_when_source_has_no_view(self):
        """Test that error is raised when source has no view configuration."""
        # Arrange
        source = SourceConfig(
            name="test_source",
            url="http://example.com/data.csv",
            file="data.csv",
            kind=SourceKind.TABULAR,
            separator=",",
            attributes=AttributesConfig(
                original=[OriginalAttributeConfig(name="id", type=DataType.INTEGER)]
            ),
        )

        builder = ViewBuilder()

        # Act & Assert
        with pytest.raises(ValueError, match="has no view configuration"):
            builder.build_create_view(source, "test_view")
