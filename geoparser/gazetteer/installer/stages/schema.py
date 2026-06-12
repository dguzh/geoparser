from typing import Any, Dict

import sqlalchemy as sa

from geoparser.db.db import get_connection
from geoparser.gazetteer.installer.model import SourceConfig
from geoparser.gazetteer.installer.queries.ddl import TableBuilder
from geoparser.gazetteer.installer.stages.base import Stage
from geoparser.gazetteer.installer.utils.progress import create_progress_bar

VIEW_SUFFIX = "_view"


class SchemaStage(Stage):
    """
    Creates database tables.

    This stage uses query builders to construct and execute DDL statements
    for creating tables based on source configurations. Views are created
    later (after geometries and spatial joins are available).
    """

    def __init__(self):
        """Initialize the schema stage with query builders."""
        super().__init__(
            name="Schema",
            description="Create database tables",
        )
        self.table_builder = TableBuilder()

    def execute(self, source: SourceConfig, context: Dict[str, Any]) -> None:
        """
        Create the table for a source.

        Args:
            source: Source configuration
            context: Shared context (will be populated with 'table_name')
        """
        table_name = self._create_table(source)
        context["table_name"] = table_name

    def _create_table(self, source: SourceConfig) -> str:
        """
        Create a table for a source.

        Args:
            source: Source configuration

        Returns:
            Name of the created table
        """
        table_name = source.name

        with create_progress_bar(1, f"Creating {table_name}", "table") as pbar:
            # Drop existing view and table if they exist
            self._drop_existing(table_name)

            # Create new table
            create_sql = self.table_builder.build_create_table(source, table_name)

            with get_connection() as connection:
                connection.execute(sa.text(create_sql))
                connection.commit()

            pbar.update(1)

        return table_name

    def _drop_existing(self, table_name: str) -> None:
        """
        Drop an existing table (and its view) if they exist.

        Args:
            table_name: Name of the table to drop
        """
        view_name = f"{table_name}{VIEW_SUFFIX}"

        with get_connection() as connection:
            connection.execute(sa.text(f"DROP VIEW IF EXISTS {view_name}"))
            connection.execute(sa.text(f"DROP TABLE IF EXISTS {table_name}"))
            connection.commit()
