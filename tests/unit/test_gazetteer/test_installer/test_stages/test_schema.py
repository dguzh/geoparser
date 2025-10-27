"""
Unit tests for geoparser/gazetteer/installer/stages/schema.py

Tests the SchemaStage class.
"""

from unittest.mock import Mock, patch

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


@pytest.mark.unit
class TestSchemaStageDropExistingTable:
    """Test SchemaStage._drop_existing_table() method."""

    def test_falls_back_to_drop_table_on_spatialite_error(self):
        """Test that standard DROP TABLE is used when DropTable() fails."""
        # Arrange
        import sqlalchemy as sa

        stage = SchemaStage()

        # Mock connection that fails on DropTable but succeeds on DROP TABLE
        mock_connection = Mock()
        # First execute raises error, second succeeds
        execute_calls = []

        def mock_execute(stmt):
            execute_calls.append(str(stmt))
            if len(execute_calls) == 1:
                raise sa.exc.DatabaseError(
                    "statement", {}, Exception("DropTable failed")
                )
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
            stage._drop_existing_table("test_table")

        # Assert - Should call execute twice (DropTable, then DROP TABLE)
        assert len(execute_calls) == 2
        assert "DropTable" in execute_calls[0]
        assert "DROP TABLE" in execute_calls[1]
        # commit should be called once at the end
        assert mock_connection.commit.call_count == 1
