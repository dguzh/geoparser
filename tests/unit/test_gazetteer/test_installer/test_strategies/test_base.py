"""
Unit tests for geoparser/gazetteer/installer/strategies/base.py

Tests the LoadStrategy abstract base class.
"""

from pathlib import Path

import pytest

from geoparser.gazetteer.installer.model import (
    AttributesConfig,
    DataType,
    OriginalAttributeConfig,
    SourceConfig,
    SourceType,
)
from geoparser.gazetteer.installer.strategies.base import LoadStrategy


class ConcreteLoadStrategy(LoadStrategy):
    """Concrete implementation of LoadStrategy for testing."""

    def __init__(self):
        self.loaded = False
        self.source_received = None
        self.file_path_received = None
        self.table_name_received = None
        self.chunksize_received = None

    def load(self, source, file_path, table_name, chunksize):
        """Load data (test implementation)."""
        self.loaded = True
        self.source_received = source
        self.file_path_received = file_path
        self.table_name_received = table_name
        self.chunksize_received = chunksize


@pytest.mark.unit
class TestLoadStrategy:
    """Test LoadStrategy abstract base class."""

    def test_cannot_instantiate_abstract_strategy(self):
        """Test that abstract LoadStrategy cannot be instantiated directly."""
        # Act & Assert
        with pytest.raises(TypeError):
            LoadStrategy()

    def test_concrete_strategy_can_be_instantiated(self):
        """Test that concrete implementation can be instantiated."""
        # Act
        strategy = ConcreteLoadStrategy()

        # Assert
        assert strategy is not None

    def test_load_method_receives_parameters(self):
        """Test that load method receives all parameters."""
        # Arrange
        strategy = ConcreteLoadStrategy()
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
        file_path = Path("/tmp/data.csv")
        table_name = "test_table"
        chunksize = 10000

        # Act
        strategy.load(source, file_path, table_name, chunksize)

        # Assert
        assert strategy.loaded is True
        assert strategy.source_received == source
        assert strategy.file_path_received == file_path
        assert strategy.table_name_received == table_name
        assert strategy.chunksize_received == chunksize
