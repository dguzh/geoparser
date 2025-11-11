"""
Unit tests for geoparser/gazetteer/installer/stages/ingestion.py

Tests the IngestionStage class.
"""

import pytest

from geoparser.gazetteer.installer.model import SourceType
from geoparser.gazetteer.installer.stages.ingestion import IngestionStage


@pytest.mark.unit
class TestIngestionStageInit:
    """Test IngestionStage initialization."""

    def test_initializes_with_default_chunksize(self):
        """Test that default chunksize is set."""
        # Act
        stage = IngestionStage()

        # Assert
        assert stage.chunksize == 20000

    def test_initializes_with_custom_chunksize(self):
        """Test that custom chunksize is accepted."""
        # Act
        stage = IngestionStage(chunksize=10000)

        # Assert
        assert stage.chunksize == 10000

    def test_initializes_strategies_for_both_source_types(self):
        """Test that strategies are initialized for both source types."""
        # Act
        stage = IngestionStage()

        # Assert
        assert SourceType.TABULAR in stage.strategies
        assert SourceType.SPATIAL in stage.strategies

    def test_sets_name_and_description(self):
        """Test that stage name and description are set."""
        # Act
        stage = IngestionStage()

        # Assert
        assert stage.name == "Ingestion"
        assert stage.description == "Load data into database tables"
