from abc import ABC
from typing import List


class QueryBuilder(ABC):
    """
    Abstract base class for SQL query builders.

    Query builders are responsible for constructing SQL statements
    in a composable, testable way. Each builder focuses on a specific
    type of SQL operation (DDL, DML, etc.).
    """

    @staticmethod
    def sanitize_identifier(identifier: str) -> str:
        """
        Validate and sanitize a SQL identifier.

        Args:
            identifier: SQL identifier (table name, column name, etc.)

        Returns:
            The sanitized identifier

        Raises:
            ValueError: If the identifier is invalid
        """
        if not identifier:
            raise ValueError("Identifier cannot be empty")

        # Basic validation - identifiers should be alphanumeric plus underscore
        if not all(c.isalnum() or c == "_" for c in identifier):
            raise ValueError(
                f"Invalid identifier '{identifier}': must contain only "
                "alphanumeric characters and underscores"
            )

        return identifier

    @staticmethod
    def format_column_list(columns: List[str]) -> str:
        """
        Format a list of column names as a comma-separated string.

        Args:
            columns: List of column names

        Returns:
            Comma-separated string of column names
        """
        return ", ".join(columns)

    @staticmethod
    def indent(text: str, spaces: int = 4) -> str:
        """
        Indent text by a specified number of spaces.

        Args:
            text: Text to indent
            spaces: Number of spaces to indent by

        Returns:
            Indented text
        """
        indent_str = " " * spaces
        return "\n".join(
            indent_str + line if line.strip() else line for line in text.split("\n")
        )
