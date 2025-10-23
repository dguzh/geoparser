"""
Unit tests for geoparser/gazetteer/installer/queries/base.py

Tests the QueryBuilder base class and its utility methods.
"""

import pytest

from geoparser.gazetteer.installer.queries.base import QueryBuilder


@pytest.mark.unit
class TestQueryBuilderSanitizeIdentifier:
    """Test QueryBuilder.sanitize_identifier() method."""

    def test_accepts_valid_alphanumeric_identifier(self):
        """Test that valid alphanumeric identifiers are accepted."""
        # Act
        result = QueryBuilder.sanitize_identifier("table123")

        # Assert
        assert result == "table123"

    def test_accepts_identifier_with_underscores(self):
        """Test that identifiers with underscores are accepted."""
        # Act
        result = QueryBuilder.sanitize_identifier("my_table_name")

        # Assert
        assert result == "my_table_name"

    def test_rejects_empty_identifier(self):
        """Test that empty identifiers are rejected."""
        # Act & Assert
        with pytest.raises(ValueError, match="Identifier cannot be empty"):
            QueryBuilder.sanitize_identifier("")

    def test_rejects_identifier_with_spaces(self):
        """Test that identifiers with spaces are rejected."""
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid identifier"):
            QueryBuilder.sanitize_identifier("table name")

    def test_rejects_identifier_with_special_characters(self):
        """Test that identifiers with special characters are rejected."""
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid identifier"):
            QueryBuilder.sanitize_identifier("table-name")

    def test_rejects_identifier_with_sql_injection(self):
        """Test that potential SQL injection attempts are rejected."""
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid identifier"):
            QueryBuilder.sanitize_identifier("table'; DROP TABLE users--")


@pytest.mark.unit
class TestQueryBuilderFormatColumnList:
    """Test QueryBuilder.format_column_list() method."""

    def test_formats_single_column(self):
        """Test formatting a single column."""
        # Act
        result = QueryBuilder.format_column_list(["id"])

        # Assert
        assert result == "id"

    def test_formats_multiple_columns(self):
        """Test formatting multiple columns."""
        # Act
        result = QueryBuilder.format_column_list(["id", "name", "value"])

        # Assert
        assert result == "id, name, value"

    def test_formats_empty_list(self):
        """Test formatting an empty list."""
        # Act
        result = QueryBuilder.format_column_list([])

        # Assert
        assert result == ""


@pytest.mark.unit
class TestQueryBuilderIndent:
    """Test QueryBuilder.indent() method."""

    def test_indents_single_line(self):
        """Test indenting a single line."""
        # Act
        result = QueryBuilder.indent("SELECT * FROM table")

        # Assert
        assert result == "    SELECT * FROM table"

    def test_indents_multiple_lines(self):
        """Test indenting multiple lines."""
        # Arrange
        text = "SELECT *\nFROM table\nWHERE id = 1"

        # Act
        result = QueryBuilder.indent(text)

        # Assert
        assert result == "    SELECT *\n    FROM table\n    WHERE id = 1"

    def test_indents_with_custom_spaces(self):
        """Test indenting with custom number of spaces."""
        # Act
        result = QueryBuilder.indent("SELECT * FROM table", spaces=2)

        # Assert
        assert result == "  SELECT * FROM table"

    def test_preserves_blank_lines(self):
        """Test that blank lines are preserved without indentation."""
        # Arrange
        text = "SELECT *\n\nFROM table"

        # Act
        result = QueryBuilder.indent(text)

        # Assert
        assert result == "    SELECT *\n\n    FROM table"
