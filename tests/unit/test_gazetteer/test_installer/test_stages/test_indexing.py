"""
Unit tests for geoparser/gazetteer/installer/stages/indexing.py

Tests the IndexingStage class.
"""

from unittest.mock import Mock, patch

import pytest

from geoparser.gazetteer.installer.model import (
    AttributesConfig,
    DataType,
    DerivedAttributeConfig,
    OriginalAttributeConfig,
    SourceConfig,
    SourceType,
)
from geoparser.gazetteer.installer.stages.indexing import IndexingStage


@pytest.mark.unit
class TestIndexingStageInit:
    """Test IndexingStage initialization."""

    def test_sets_name_and_description(self):
        """Test that stage name and description are set."""
        # Act
        stage = IndexingStage()

        # Assert
        assert stage.name == "Indexing"
        assert stage.description == "Create database indices"


@pytest.mark.unit
class TestIndexingStageCollectIndexedColumns:
    """Test IndexingStage._collect_indexed_columns() method."""

    def test_returns_empty_list_when_no_indexed_columns(self):
        """Test that empty list is returned when no columns are indexed."""
        # Arrange
        source = SourceConfig(
            name="test",
            url="http://example.com/data.csv",
            file="data.csv",
            type=SourceType.TABULAR,
            separator=",",
            attributes=AttributesConfig(
                original=[
                    OriginalAttributeConfig(
                        name="id", type=DataType.INTEGER, index=False
                    ),
                    OriginalAttributeConfig(
                        name="name", type=DataType.TEXT, index=False
                    ),
                ]
            ),
        )

        stage = IndexingStage()

        # Act
        result = stage._collect_indexed_columns(source)

        # Assert
        assert result == []

    def test_collects_indexed_original_columns(self):
        """Test that indexed original columns are collected."""
        # Arrange
        source = SourceConfig(
            name="test",
            url="http://example.com/data.csv",
            file="data.csv",
            type=SourceType.TABULAR,
            separator=",",
            attributes=AttributesConfig(
                original=[
                    OriginalAttributeConfig(
                        name="id", type=DataType.INTEGER, index=True
                    ),
                    OriginalAttributeConfig(
                        name="name", type=DataType.TEXT, index=False
                    ),
                ]
            ),
        )

        stage = IndexingStage()

        # Act
        result = stage._collect_indexed_columns(source)

        # Assert
        assert len(result) == 1
        assert result[0] == ("id", DataType.INTEGER)

    def test_collects_indexed_derived_columns(self):
        """Test that indexed derived columns are collected."""
        # Arrange
        source = SourceConfig(
            name="test",
            url="http://example.com/data.csv",
            file="data.csv",
            type=SourceType.TABULAR,
            separator=",",
            attributes=AttributesConfig(
                original=[
                    OriginalAttributeConfig(name="first", type=DataType.TEXT),
                ],
                derived=[
                    DerivedAttributeConfig(
                        name="full_name",
                        type=DataType.TEXT,
                        expression="first || ' ' || last",
                        index=True,
                    )
                ],
            ),
        )

        stage = IndexingStage()

        # Act
        result = stage._collect_indexed_columns(source)

        # Assert
        assert len(result) == 1
        assert result[0] == ("full_name", DataType.TEXT)

    def test_excludes_dropped_columns(self):
        """Test that dropped columns are not included even if indexed."""
        # Arrange
        source = SourceConfig(
            name="test",
            url="http://example.com/data.csv",
            file="data.csv",
            type=SourceType.TABULAR,
            separator=",",
            attributes=AttributesConfig(
                original=[
                    OriginalAttributeConfig(
                        name="temp", type=DataType.TEXT, index=True, drop=True
                    ),
                    OriginalAttributeConfig(
                        name="id", type=DataType.INTEGER, index=True
                    ),
                ]
            ),
        )

        stage = IndexingStage()

        # Act
        result = stage._collect_indexed_columns(source)

        # Assert
        assert len(result) == 1
        assert result[0] == ("id", DataType.INTEGER)

    def test_collects_both_original_and_derived_indexed_columns(self):
        """Test that both original and derived indexed columns are collected."""
        # Arrange
        source = SourceConfig(
            name="test",
            url="http://example.com/data.csv",
            file="data.csv",
            type=SourceType.TABULAR,
            separator=",",
            attributes=AttributesConfig(
                original=[
                    OriginalAttributeConfig(
                        name="id", type=DataType.INTEGER, index=True
                    ),
                ],
                derived=[
                    DerivedAttributeConfig(
                        name="computed",
                        type=DataType.REAL,
                        expression="id * 2",
                        index=True,
                    )
                ],
            ),
        )

        stage = IndexingStage()

        # Act
        result = stage._collect_indexed_columns(source)

        # Assert
        assert len(result) == 2
        assert ("id", DataType.INTEGER) in result
        assert ("computed", DataType.REAL) in result


@pytest.mark.unit
class TestIndexingStageExecute:
    """Test IndexingStage.execute() method."""

    def test_skips_when_no_indexed_columns(self):
        """Test that indexing is skipped when there are no indexed columns."""
        # Arrange
        source = SourceConfig(
            name="test",
            path="/test/data.csv",
            file="data.csv",
            type=SourceType.TABULAR,
            separator=",",
            attributes=AttributesConfig(
                original=[
                    OriginalAttributeConfig(
                        name="id", type=DataType.INTEGER, index=False
                    ),
                    OriginalAttributeConfig(
                        name="name", type=DataType.TEXT, index=False
                    ),
                ]
            ),
        )

        stage = IndexingStage()
        context = {"table_name": "test_table"}

        # Mock get_connection
        mock_get_connection = Mock()

        # Act
        with patch(
            "geoparser.gazetteer.installer.stages.indexing.get_connection",
            mock_get_connection,
        ):
            stage.execute(source, context)

        # Assert - get_connection should not have been called because there are no indexed columns
        mock_get_connection.assert_not_called()


@pytest.mark.unit
class TestIndexingStageCreateIndices:
    """Test IndexingStage._create_indices() error handling."""

    def test_continues_on_database_error(self, capsys):
        """Test that indexing continues when an index creation fails."""
        # Arrange
        import sqlalchemy as sa

        stage = IndexingStage()
        indexed_columns = [
            ("id", DataType.INTEGER),
            ("name", DataType.TEXT),
        ]

        # Mock connection that fails on first index but succeeds on second
        mock_connection = Mock()
        mock_connection.execute.side_effect = [
            sa.exc.DatabaseError(
                "statement", {}, Exception("DB error")
            ),  # First index fails
            None,  # Second index succeeds
        ]
        mock_connection.commit = Mock()
        mock_connection.__enter__ = Mock(return_value=mock_connection)
        mock_connection.__exit__ = Mock(return_value=None)

        # Act
        with patch(
            "geoparser.gazetteer.installer.stages.indexing.get_connection",
            return_value=mock_connection,
        ):
            stage._create_indices("test_table", indexed_columns)

        # Assert - Should print warning but continue
        captured = capsys.readouterr()
        assert "Warning" in captured.out
        assert "Failed to create index" in captured.out
        # commit should still be called
        mock_connection.commit.assert_called_once()
