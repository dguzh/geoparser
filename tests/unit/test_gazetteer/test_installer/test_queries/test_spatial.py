"""
Unit tests for geoparser/gazetteer/installer/queries/spatial.py

Tests the helpers that translate declarative spatial joins into precomputed
key columns and plain SQL equality conditions.
"""

import pytest

from geoparser.gazetteer.installer.model import (
    JoinOperandConfig,
    SpatialConditionConfig,
)
from geoparser.gazetteer.installer.queries.spatial import (
    build_spatial_equality_condition,
    spatial_join_column_name,
)


@pytest.mark.unit
class TestSpatialJoinColumnName:
    """Test spatial_join_column_name()."""

    def test_builds_prefixed_column_name(self):
        """Test that the column name is prefixed with the spatial-join marker."""
        assert spatial_join_column_name("regions") == "__spatial_join_regions"


@pytest.mark.unit
class TestBuildSpatialEqualityCondition:
    """Test build_spatial_equality_condition()."""

    def test_builds_equality_on_precomputed_column(self):
        """Test that a spatial join becomes an equality on the key column."""
        # Arrange
        spatial = SpatialConditionConfig(
            predicate="within",
            left=JoinOperandConfig(column="places.geometry"),
            right=JoinOperandConfig(column="regions.geometry"),
        )

        # Act
        condition = build_spatial_equality_condition(spatial)

        # Assert
        assert condition == "places.__spatial_join_regions = regions.rowid"

    def test_uses_left_source_for_key_column_owner(self):
        """Test that the key column belongs to the left source's table."""
        # Arrange
        spatial = SpatialConditionConfig(
            predicate="within",
            left=JoinOperandConfig(column="roads.geometry", transform="centroid"),
            right=JoinOperandConfig(column="municipalities.geometry"),
        )

        # Act
        condition = build_spatial_equality_condition(spatial)

        # Assert
        assert condition.startswith("roads.__spatial_join_municipalities = ")
        assert condition.endswith("municipalities.rowid")
