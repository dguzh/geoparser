"""
Unit tests for geoparser/gazetteer/installer/stages/schema.py

Tests the SchemaStage class.
"""

import pytest

from geoparser.gazetteer.installer.stages.schema import SchemaStage


@pytest.mark.unit
class TestSchemaStageConstants:
    """Test SchemaStage constants."""

    def test_has_view_suffix_constant(self):
        """Test that VIEW_SUFFIX constant is defined."""
        assert SchemaStage.VIEW_SUFFIX == "_view"


@pytest.mark.unit
class TestSchemaStageInit:
    """Test SchemaStage initialization."""

    def test_initializes_table_builder(self):
        """Test that TableBuilder is initialized."""
        # Act
        stage = SchemaStage()

        # Assert
        assert stage.table_builder is not None
        assert hasattr(stage.table_builder, "build_create_table")

    def test_initializes_view_builder(self):
        """Test that ViewBuilder is initialized."""
        # Act
        stage = SchemaStage()

        # Assert
        assert stage.view_builder is not None
        assert hasattr(stage.view_builder, "build_create_view")

    def test_sets_name_and_description(self):
        """Test that stage name and description are set."""
        # Act
        stage = SchemaStage()

        # Assert
        assert stage.name == "Schema"
        assert stage.description == "Create database tables and views"
