"""
Unit tests for geoparser/gazetteer/installer/utils/chunking.py

Tests the count_rows and iter_rowid_ranges utility functions.
"""

from unittest.mock import Mock

import pytest

from geoparser.gazetteer.installer.utils.chunking import (
    CHUNKSIZE,
    count_rows,
    iter_rowid_ranges,
)


@pytest.mark.unit
class TestCountRows:
    """Test count_rows() function."""

    def test_returns_max_rowid(self):
        """Test that the row count is derived from the maximum rowid."""
        # Arrange
        mock_connection = Mock()
        mock_connection.execute.return_value.scalar.return_value = 42

        # Act
        result = count_rows(mock_connection, "test_table")

        # Assert
        assert result == 42

    def test_returns_zero_for_empty_table(self):
        """Test that an empty table (MAX(rowid) is NULL) counts as zero."""
        # Arrange
        mock_connection = Mock()
        mock_connection.execute.return_value.scalar.return_value = None

        # Act
        result = count_rows(mock_connection, "test_table")

        # Assert
        assert result == 0


@pytest.mark.unit
class TestIterRowidRanges:
    """Test iter_rowid_ranges() function."""

    def test_splits_into_inclusive_chunks(self):
        """Test that rows are split into consecutive inclusive ranges."""
        # Act
        ranges = list(iter_rowid_ranges(total_rows=5, chunksize=2))

        # Assert
        assert ranges == [(1, 2), (3, 4), (5, 5)]

    def test_single_chunk_when_chunksize_exceeds_rows(self):
        """Test that all rows fit in one chunk when chunksize is large."""
        # Act
        ranges = list(iter_rowid_ranges(total_rows=3, chunksize=20000))

        # Assert
        assert ranges == [(1, 3)]

    def test_exact_multiple_of_chunksize(self):
        """Test ranges when total rows is an exact multiple of chunksize."""
        # Act
        ranges = list(iter_rowid_ranges(total_rows=4, chunksize=2))

        # Assert
        assert ranges == [(1, 2), (3, 4)]

    def test_yields_nothing_for_empty_table(self):
        """Test that no ranges are produced when there are no rows."""
        # Act
        ranges = list(iter_rowid_ranges(total_rows=0, chunksize=2))

        # Assert
        assert ranges == []


@pytest.mark.unit
def test_chunksize():
    assert CHUNKSIZE == 100_000
