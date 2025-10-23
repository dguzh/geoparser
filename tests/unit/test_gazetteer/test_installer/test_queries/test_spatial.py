"""
Unit tests for geoparser/gazetteer/installer/queries/spatial.py

Tests the SpatialOptimizer class for optimizing spatial queries.
"""

import pytest

from geoparser.gazetteer.installer.queries.spatial import SpatialOptimizer


@pytest.mark.unit
class TestSpatialOptimizerOptimizeJoinCondition:
    """Test SpatialOptimizer.optimize_join_condition() method."""

    def test_optimizes_st_within_condition(self):
        """Test optimizing ST_Within join condition."""
        # Arrange
        optimizer = SpatialOptimizer()
        condition = "ST_Within(geometry1, table2.geometry2)"

        # Act
        result = optimizer.optimize_join_condition(condition)

        # Assert
        assert "table2.rowid IN" in result
        assert "SELECT rowid FROM SpatialIndex" in result
        assert "f_table_name = 'table2'" in result
        assert "search_frame = geometry1" in result
        assert "ST_Within(geometry1, table2.geometry2)" in result

    def test_optimizes_st_intersects_condition(self):
        """Test optimizing ST_Intersects join condition."""
        # Arrange
        optimizer = SpatialOptimizer()
        condition = "ST_Intersects(geom1, table2.geom2)"

        # Act
        result = optimizer.optimize_join_condition(condition)

        # Assert
        assert "table2.rowid IN" in result
        assert "ST_Intersects(geom1, table2.geom2)" in result

    def test_optimizes_st_contains_condition(self):
        """Test optimizing ST_Contains join condition."""
        # Arrange
        optimizer = SpatialOptimizer()
        condition = "ST_Contains(geometry, table2.geometry)"

        # Act
        result = optimizer.optimize_join_condition(condition)

        # Assert
        assert "table2.rowid IN" in result
        assert "ST_Contains(geometry, table2.geometry)" in result

    def test_optimizes_centroid_condition(self):
        """Test optimizing ST_Within with ST_Centroid."""
        # Arrange
        optimizer = SpatialOptimizer()
        condition = "ST_Within(ST_Centroid(table1.geom), table2.geom)"

        # Act
        result = optimizer.optimize_join_condition(condition)

        # Assert
        assert "table2.rowid IN" in result
        assert "search_frame = ST_Centroid(table1.geom)" in result
        assert "ST_Within(ST_Centroid(table1.geom), table2.geom)" in result

    def test_returns_original_for_non_spatial_condition(self):
        """Test that non-spatial conditions are returned unchanged."""
        # Arrange
        optimizer = SpatialOptimizer()
        condition = "table1.id = table2.ref_id"

        # Act
        result = optimizer.optimize_join_condition(condition)

        # Assert
        assert result == condition

    def test_handles_complex_geometry_expression(self):
        """Test optimizing condition with complex geometry expression."""
        # Arrange
        optimizer = SpatialOptimizer()
        condition = "ST_Within(table1.geometry, table2.boundary)"

        # Act
        result = optimizer.optimize_join_condition(condition)

        # Assert
        assert "search_frame = table1.geometry" in result
        assert "f_table_name = 'table2'" in result


@pytest.mark.unit
class TestSpatialOptimizerBuildIndexCondition:
    """Test SpatialOptimizer._build_index_condition() method."""

    def test_builds_index_lookup_condition(self):
        """Test building spatial index lookup condition."""
        # Arrange
        optimizer = SpatialOptimizer()

        # Act
        result = optimizer._build_index_condition("test_table", "geometry_expr")

        # Assert
        assert result == (
            "test_table.rowid IN ("
            "SELECT rowid FROM SpatialIndex "
            "WHERE f_table_name = 'test_table' "
            "AND search_frame = geometry_expr)"
        )

    def test_uses_correct_table_name(self):
        """Test that table name is correctly included."""
        # Arrange
        optimizer = SpatialOptimizer()

        # Act
        result = optimizer._build_index_condition("my_table", "geom")

        # Assert
        assert "my_table.rowid IN" in result
        assert "f_table_name = 'my_table'" in result

    def test_uses_correct_geometry_expression(self):
        """Test that geometry expression is correctly included."""
        # Arrange
        optimizer = SpatialOptimizer()

        # Act
        result = optimizer._build_index_condition("table", "ST_Centroid(geom)")

        # Assert
        assert "search_frame = ST_Centroid(geom)" in result


@pytest.mark.unit
class TestSpatialOptimizerConstants:
    """Test SpatialOptimizer constants."""

    def test_has_spatial_functions_list(self):
        """Test that SPATIAL_FUNCTIONS list contains expected functions."""
        # Assert
        assert "ST_Within" in SpatialOptimizer.SPATIAL_FUNCTIONS
        assert "ST_Intersects" in SpatialOptimizer.SPATIAL_FUNCTIONS
        assert "ST_Contains" in SpatialOptimizer.SPATIAL_FUNCTIONS
        assert "ST_Overlaps" in SpatialOptimizer.SPATIAL_FUNCTIONS

    def test_has_spatial_index_table_constant(self):
        """Test that SPATIAL_INDEX_TABLE constant is set."""
        # Assert
        assert SpatialOptimizer.SPATIAL_INDEX_TABLE == "SpatialIndex"

    def test_has_table_name_column_constant(self):
        """Test that TABLE_NAME_COLUMN constant is set."""
        # Assert
        assert SpatialOptimizer.TABLE_NAME_COLUMN == "f_table_name"
