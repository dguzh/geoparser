"""
Unit tests for geoparser/gazetteer/installer/queries/dml.py

Tests the TransformationBuilder and FeatureRegistrationBuilder classes.
"""

import pytest

from geoparser.gazetteer.installer.model import (
    AttributesConfig,
    ColumnConfig,
    DataType,
    FeatureConfig,
    NameColumnConfig,
    OriginalAttributeConfig,
    SourceConfig,
    SourceType,
)
from geoparser.gazetteer.installer.queries.dml import (
    FeatureRegistrationBuilder,
    TransformationBuilder,
)


@pytest.mark.unit
class TestTransformationBuilderBuildDerivationUpdate:
    """Test TransformationBuilder.build_derivation_update() method."""

    def test_builds_derivation_update(self):
        """Test building UPDATE statement for derived column."""
        # Arrange
        builder = TransformationBuilder()

        # Act
        sql = builder.build_derivation_update(
            "test_table", "full_name", "first_name || ' ' || last_name"
        )

        # Assert
        assert sql == "UPDATE test_table SET full_name = first_name || ' ' || last_name"

    def test_sanitizes_table_name(self):
        """Test that table name is sanitized."""
        # Arrange
        builder = TransformationBuilder()

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid identifier"):
            builder.build_derivation_update("table-name", "col", "expression")

    def test_sanitizes_column_name(self):
        """Test that column name is sanitized."""
        # Arrange
        builder = TransformationBuilder()

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid identifier"):
            builder.build_derivation_update("table", "col-name", "expression")


@pytest.mark.unit
class TestTransformationBuilderBuildGeometryUpdate:
    """Test TransformationBuilder.build_geometry_update() method."""

    def test_builds_geometry_update(self):
        """Test building UPDATE statement to convert WKT to geometry."""
        # Arrange
        builder = TransformationBuilder()

        # Act
        sql = builder.build_geometry_update("test_table", "geometry", 4326)

        # Assert
        assert sql == (
            "UPDATE test_table "
            "SET geometry = GeomFromText(geometry_wkt, 4326) "
            "WHERE geometry_wkt IS NOT NULL"
        )

    def test_uses_wkt_column_suffix(self):
        """Test that _wkt suffix is used for source column."""
        # Arrange
        builder = TransformationBuilder()

        # Act
        sql = builder.build_geometry_update("test_table", "geom", 3857)

        # Assert
        assert "geom_wkt" in sql
        assert "GeomFromText(geom_wkt, 3857)" in sql


@pytest.mark.unit
class TestFeatureRegistrationBuilderBuildFeatureInsert:
    """Test FeatureRegistrationBuilder.build_feature_insert() method."""

    def test_builds_feature_insert(self):
        """Test building INSERT statement for features."""
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
            features=FeatureConfig(
                identifier=[ColumnConfig(column="id")],
                names=[NameColumnConfig(column="name")],
            ),
        )

        builder = FeatureRegistrationBuilder()

        # Act
        sql = builder.build_feature_insert(source, source_id=123)

        # Assert
        assert "INSERT OR IGNORE INTO feature" in sql
        assert "source_id, location_id_value" in sql
        assert "123 as source_id" in sql
        assert "CAST(id AS TEXT) as location_id_value" in sql
        assert "FROM test_source" in sql
        assert "WHERE id IS NOT NULL" in sql

    def test_raises_error_when_source_has_no_features(self):
        """Test that error is raised when source has no feature configuration."""
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

        builder = FeatureRegistrationBuilder()

        # Act & Assert
        with pytest.raises(ValueError, match="has no feature configuration"):
            builder.build_feature_insert(source, source_id=123)


@pytest.mark.unit
class TestFeatureRegistrationBuilderBuildNameInsert:
    """Test FeatureRegistrationBuilder.build_name_insert() method."""

    def test_builds_name_insert(self):
        """Test building INSERT statement for simple names."""
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
            features=FeatureConfig(
                identifier=[ColumnConfig(column="id")],
                names=[NameColumnConfig(column="name")],
            ),
        )

        builder = FeatureRegistrationBuilder()

        # Act
        sql = builder.build_name_insert(source, source_id=123, name_column="name")

        # Assert
        assert "INSERT OR IGNORE INTO name" in sql
        assert "text, feature_id" in sql
        assert "s.name as text" in sql
        assert "f.id as feature_id" in sql
        assert "FROM test_source s" in sql
        assert "JOIN feature f ON f.source_id = 123" in sql
        assert "WHERE s.name IS NOT NULL AND s.name != ''" in sql

    def test_raises_error_when_source_has_no_features(self):
        """Test that error is raised when source has no feature configuration."""
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

        builder = FeatureRegistrationBuilder()

        # Act & Assert
        with pytest.raises(ValueError, match="has no feature configuration"):
            builder.build_name_insert(source, source_id=123, name_column="name")


@pytest.mark.unit
class TestFeatureRegistrationBuilderBuildNameInsertSeparated:
    """Test FeatureRegistrationBuilder.build_name_insert_separated() method."""

    def test_builds_separated_name_insert(self):
        """Test building INSERT statement for separated names."""
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
                    OriginalAttributeConfig(name="names", type=DataType.TEXT),
                ]
            ),
            features=FeatureConfig(
                identifier=[ColumnConfig(column="id")],
                names=[NameColumnConfig(column="names", separator="|")],
            ),
        )

        builder = FeatureRegistrationBuilder()

        # Act
        sql = builder.build_name_insert_separated(
            source, source_id=123, name_column="names", separator="|"
        )

        # Assert
        assert "INSERT OR IGNORE INTO name" in sql
        assert "WITH RECURSIVE split_names" in sql
        assert "feature_id, name_value, remaining" in sql
        assert "s.names || '|' as remaining" in sql
        assert "FROM test_source s" in sql
        assert "JOIN feature f ON f.source_id = 123" in sql

    def test_uses_separator_in_recursive_cte(self):
        """Test that separator is correctly used in recursive CTE."""
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
            features=FeatureConfig(
                identifier=[ColumnConfig(column="id")],
                names=[NameColumnConfig(column="names", separator=",")],
            ),
        )

        builder = FeatureRegistrationBuilder()

        # Act
        sql = builder.build_name_insert_separated(
            source, source_id=123, name_column="names", separator=","
        )

        # Assert
        assert "|| ',' as remaining" in sql
        assert "instr(remaining, ',')" in sql

    def test_raises_error_when_source_has_no_features(self):
        """Test that error is raised when source has no feature configuration."""
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

        builder = FeatureRegistrationBuilder()

        # Act & Assert
        with pytest.raises(ValueError, match="has no feature configuration"):
            builder.build_name_insert_separated(
                source, source_id=123, name_column="names", separator=","
            )
