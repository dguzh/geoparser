"""
Unit tests for geoparser/gazetteer/installer/stages/schema.py

Tests the SchemaStage class.
"""

from unittest.mock import Mock, patch

import pytest

from geoparser.gazetteer.installer.stages.schema import VIEW_SUFFIX, SchemaStage


@pytest.mark.unit
class TestSchemaStageConstants:
    """Test schema module constants."""

    def test_has_view_suffix_constant(self):
        """Test that VIEW_SUFFIX constant is defined."""
        assert VIEW_SUFFIX == "_view"


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

    def test_sets_name_and_description(self):
        """Test that stage name and description are set."""
        # Act
        stage = SchemaStage()

        # Assert
        assert stage.name == "Schema"
        assert stage.description == "Create database tables"


@pytest.mark.unit
class TestSchemaStageDropExisting:
    """Test SchemaStage._drop_existing() method."""

    def test_drops_view_and_table(self):
        """Test that both the view and table are dropped with plain SQL."""
        # Arrange
        stage = SchemaStage()

        mock_connection = Mock()
        execute_calls = []

        def mock_execute(stmt):
            execute_calls.append(str(stmt))
            return None

        mock_connection.execute = mock_execute
        mock_connection.commit = Mock()
        mock_connection.__enter__ = Mock(return_value=mock_connection)
        mock_connection.__exit__ = Mock(return_value=None)

        # Act
        with patch(
            "geoparser.gazetteer.installer.stages.schema.get_connection",
            return_value=mock_connection,
        ):
            stage._drop_existing("test_table")

        # Assert
        assert len(execute_calls) == 2
        assert "DROP VIEW IF EXISTS test_table_view" in execute_calls[0]
        assert "DROP TABLE IF EXISTS test_table" in execute_calls[1]
        assert "DropTable" not in execute_calls[0]
        assert "DropTable" not in execute_calls[1]
        assert mock_connection.commit.call_count == 1
