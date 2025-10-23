"""
Unit tests for geoparser/gazetteer/installer/strategies/tabular.py

Tests the TabularLoadStrategy class.
"""

import pytest

from geoparser.gazetteer.installer.model import (
    AttributesConfig,
    DataType,
    OriginalAttributeConfig,
    SourceConfig,
    SourceType,
)
from geoparser.gazetteer.installer.strategies.tabular import TabularLoadStrategy


@pytest.mark.unit
class TestTabularLoadStrategyGetColumnNames:
    """Test TabularLoadStrategy._get_column_names() method."""

    def test_extracts_column_names_from_source(self):
        """Test that column names are extracted from source attributes."""
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
                    OriginalAttributeConfig(name="value", type=DataType.REAL),
                ]
            ),
        )

        strategy = TabularLoadStrategy()

        # Act
        result = strategy._get_column_names(source)

        # Assert
        assert result == ["id", "name", "value"]

    def test_includes_dropped_columns_in_names(self):
        """Test that dropped columns are included in column names list."""
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
                    OriginalAttributeConfig(name="temp", type=DataType.TEXT, drop=True),
                    OriginalAttributeConfig(name="name", type=DataType.TEXT),
                ]
            ),
        )

        strategy = TabularLoadStrategy()

        # Act
        result = strategy._get_column_names(source)

        # Assert
        assert result == ["id", "temp", "name"]


@pytest.mark.unit
class TestTabularLoadStrategyGetDtypeMapping:
    """Test TabularLoadStrategy._get_dtype_mapping() method."""

    def test_maps_text_to_str(self):
        """Test that TEXT type is mapped to 'str'."""
        # Arrange
        source = SourceConfig(
            name="test",
            url="http://example.com/data.csv",
            file="data.csv",
            type=SourceType.TABULAR,
            separator=",",
            attributes=AttributesConfig(
                original=[OriginalAttributeConfig(name="name", type=DataType.TEXT)]
            ),
        )

        strategy = TabularLoadStrategy()

        # Act
        result = strategy._get_dtype_mapping(source)

        # Assert
        assert result == {"name": "str"}

    def test_maps_integer_to_int64(self):
        """Test that INTEGER type is mapped to 'Int64' (nullable)."""
        # Arrange
        source = SourceConfig(
            name="test",
            url="http://example.com/data.csv",
            file="data.csv",
            type=SourceType.TABULAR,
            separator=",",
            attributes=AttributesConfig(
                original=[OriginalAttributeConfig(name="id", type=DataType.INTEGER)]
            ),
        )

        strategy = TabularLoadStrategy()

        # Act
        result = strategy._get_dtype_mapping(source)

        # Assert
        assert result == {"id": "Int64"}

    def test_maps_real_to_float64(self):
        """Test that REAL type is mapped to 'float64'."""
        # Arrange
        source = SourceConfig(
            name="test",
            url="http://example.com/data.csv",
            file="data.csv",
            type=SourceType.TABULAR,
            separator=",",
            attributes=AttributesConfig(
                original=[OriginalAttributeConfig(name="value", type=DataType.REAL)]
            ),
        )

        strategy = TabularLoadStrategy()

        # Act
        result = strategy._get_dtype_mapping(source)

        # Assert
        assert result == {"value": "float64"}

    def test_skips_geometry_columns(self):
        """Test that GEOMETRY columns are skipped."""
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
                    OriginalAttributeConfig(
                        name="geometry", type=DataType.GEOMETRY, srid=4326
                    ),
                ]
            ),
        )

        strategy = TabularLoadStrategy()

        # Act
        result = strategy._get_dtype_mapping(source)

        # Assert
        assert result == {"id": "Int64"}
        assert "geometry" not in result

    def test_maps_multiple_columns(self):
        """Test that multiple columns of different types are mapped correctly."""
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
                    OriginalAttributeConfig(name="value", type=DataType.REAL),
                ]
            ),
        )

        strategy = TabularLoadStrategy()

        # Act
        result = strategy._get_dtype_mapping(source)

        # Assert
        assert result == {
            "id": "Int64",
            "name": "str",
            "value": "float64",
        }
