"""
Unit tests for geoparser/gazetteer/installer/strategies/spatial.py

Tests the SpatialLoadStrategy class.
"""

import pytest

from geoparser.gazetteer.installer.model import (
    AttributesConfig,
    DataType,
    OriginalAttributeConfig,
    SourceConfig,
    SourceType,
)
from geoparser.gazetteer.installer.strategies.spatial import SpatialLoadStrategy


@pytest.mark.unit
class TestSpatialLoadStrategyBuildReadKwargs:
    """Test SpatialLoadStrategy._build_read_kwargs() method."""

    def test_returns_empty_dict_when_no_layer(self):
        """Test that empty dict is returned when no layer specified."""
        # Arrange
        source = SourceConfig(
            name="test",
            url="http://example.com/data.shp",
            file="data.shp",
            type=SourceType.SPATIAL,
            attributes=AttributesConfig(
                original=[
                    OriginalAttributeConfig(
                        name="geometry", type=DataType.GEOMETRY, srid=4326
                    )
                ]
            ),
        )

        strategy = SpatialLoadStrategy()

        # Act
        result = strategy._build_read_kwargs(source)

        # Assert
        assert result == {}

    def test_includes_layer_when_specified(self):
        """Test that layer is included in kwargs when specified."""
        # Arrange
        source = SourceConfig(
            name="test",
            url="http://example.com/data.gpkg",
            file="data.gpkg",
            type=SourceType.SPATIAL,
            layer="layer1",
            attributes=AttributesConfig(
                original=[
                    OriginalAttributeConfig(
                        name="geometry", type=DataType.GEOMETRY, srid=4326
                    )
                ]
            ),
        )

        strategy = SpatialLoadStrategy()

        # Act
        result = strategy._build_read_kwargs(source)

        # Assert
        assert result == {"layer": "layer1"}


@pytest.mark.unit
class TestSpatialLoadStrategyFindGeometryAttribute:
    """Test SpatialLoadStrategy._find_geometry_attribute() method."""

    def test_finds_geometry_in_original_attributes(self):
        """Test that geometry attribute is found in original attributes."""
        # Arrange
        source = SourceConfig(
            name="test",
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

        strategy = SpatialLoadStrategy()

        # Act
        result = strategy._find_geometry_attribute(source)

        # Assert
        assert result is not None
        assert result.name == "geometry"

    def test_returns_none_when_geometry_dropped(self):
        """Test that None is returned when geometry column is dropped."""
        # Arrange
        source = SourceConfig(
            name="test",
            url="http://example.com/data.shp",
            file="data.shp",
            type=SourceType.SPATIAL,
            attributes=AttributesConfig(
                original=[
                    OriginalAttributeConfig(name="id", type=DataType.INTEGER),
                    OriginalAttributeConfig(
                        name="geometry", type=DataType.GEOMETRY, srid=4326, drop=True
                    ),
                ]
            ),
        )

        strategy = SpatialLoadStrategy()

        # Act
        result = strategy._find_geometry_attribute(source)

        # Assert
        assert result is None

    def test_returns_none_when_no_geometry(self):
        """Test that None is returned when no geometry attribute exists."""
        # Arrange
        source = SourceConfig(
            name="test",
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
        )

        strategy = SpatialLoadStrategy()

        # Act
        result = strategy._find_geometry_attribute(source)

        # Assert
        assert result is None
