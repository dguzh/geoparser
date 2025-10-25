from typing import Any, Dict

import sqlalchemy as sa

from geoparser.db.engine import get_engine
from geoparser.gazetteer.installer.model import SourceConfig
from geoparser.gazetteer.installer.queries.ddl import TableBuilder, ViewBuilder
from geoparser.gazetteer.installer.stages.base import Stage
from geoparser.gazetteer.installer.utils.progress import create_progress_bar


class SchemaStage(Stage):
    """
    Creates database schema (tables and views).

    This stage uses query builders to construct and execute DDL statements
    for creating tables and views based on source configurations.
    """

    VIEW_SUFFIX = "_view"

    def __init__(self):
        """Initialize the schema stage with query builders."""
        super().__init__(
            name="Schema",
            description="Create database tables and views",
        )
        self.table_builder = TableBuilder()
        self.view_builder = ViewBuilder()

    def execute(self, source: SourceConfig, context: Dict[str, Any]) -> None:
        """
        Create table and view for a source.

        Args:
            source: Source configuration
            context: Shared context (will be populated with 'table_name' and 'view_name')
        """
        table_name = self._create_table(source)
        context["table_name"] = table_name

        view_name = None
        if source.view:
            view_name = self._create_view(source)

        context["view_name"] = view_name

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
            # Drop existing table if it exists
            self._drop_existing_table(table_name)

            # Create new table
            create_sql = self.table_builder.build_create_table(source, table_name)

            with get_engine().connect() as connection:
                connection.execute(sa.text(create_sql))
                connection.commit()

            pbar.update(1)

        return table_name

    def _drop_existing_table(self, table_name: str) -> None:
        """
        Drop an existing table if it exists.

        Uses SpatiaLite's DropTable function for spatial tables,
        falling back to standard DROP TABLE for non-spatial tables.

        Args:
            table_name: Name of the table to drop
        """
        with get_engine().connect() as connection:
            try:
                # Try SpatiaLite's DropTable first (handles spatial tables)
                connection.execute(
                    sa.text(f"SELECT DropTable(NULL, '{table_name}', 1)")
                )
            except sa.exc.DatabaseError:
                # Fall back to standard DROP TABLE
                connection.execute(sa.text(f"DROP TABLE IF EXISTS {table_name}"))

            connection.commit()

    def _create_view(self, source: SourceConfig) -> str:
        """
        Create a view for a source.

        Args:
            source: Source configuration with view definition

        Returns:
            Name of the created view
        """
        view_name = f"{source.name}{self.VIEW_SUFFIX}"

        with create_progress_bar(1, f"Creating {view_name}", "view") as pbar:
            # Drop existing view if it exists
            with get_engine().connect() as connection:
                connection.execute(sa.text(f"DROP VIEW IF EXISTS {view_name}"))
                connection.commit()

            # Create new view
            create_sql = self.view_builder.build_create_view(source, view_name)

            with get_engine().connect() as connection:
                connection.execute(sa.text(create_sql))
                connection.commit()

            pbar.update(1)

        return view_name
