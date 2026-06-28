from typing import List

from geoparser.gazetteer.installer.model import DataType, SourceConfig
from geoparser.gazetteer.installer.queries.base import QueryBuilder
from geoparser.gazetteer.installer.queries.spatial import (
    build_spatial_equality_condition,
)


class TableBuilder(QueryBuilder):
    """
    Builds CREATE TABLE statements for gazetteer sources.

    This builder creates table schemas based on source configurations,
    handling both regular columns and geometry columns (stored as WKT text).
    """

    def build_create_table(self, source: SourceConfig, table_name: str) -> str:
        """
        Build a CREATE TABLE statement for a source.

        Args:
            source: Source configuration
            table_name: Name for the table

        Returns:
            SQL CREATE TABLE statement
        """
        self.sanitize_identifier(table_name)

        column_definitions = self._build_column_definitions(source)
        columns_sql = self.format_column_list(column_definitions)

        return f"CREATE TABLE {table_name} ({columns_sql})"

    def _build_column_definitions(self, source: SourceConfig) -> List[str]:
        """
        Build column definitions for a table.

        Args:
            source: Source configuration

        Returns:
            List of column definition strings
        """
        definitions = []

        # Add original attribute columns (excluding dropped ones)
        for attr in source.attributes.original:
            if not attr.drop:
                if attr.type == DataType.GEOMETRY:
                    # Geometry is stored as WKT text
                    definitions.append(f"{attr.name} text")
                else:
                    definitions.append(f"{attr.name} {attr.type.value}")

        # Add derived attribute columns
        for attr in source.attributes.derived:
            if attr.type == DataType.GEOMETRY:
                # Geometry is stored as WKT text
                definitions.append(f"{attr.name} text")
            else:
                definitions.append(f"{attr.name} {attr.type.value}")

        return definitions


class ViewBuilder(QueryBuilder):
    """
    Builds CREATE VIEW statements for gazetteer sources.

    This builder creates views that can join multiple sources together
    and select specific columns. Spatial joins are precomputed at install
    time, so here they are emitted as plain equality conditions.
    """

    VIEW_SUFFIX = "_view"

    def build_create_view(
        self,
        source: SourceConfig,
        view_name: str,
    ) -> str:
        """
        Build a CREATE VIEW statement for a source.

        Args:
            source: Source configuration with view definition
            view_name: Name for the view

        Returns:
            SQL CREATE VIEW statement

        Raises:
            ValueError: If source has no view configuration
        """
        if source.view is None:
            raise ValueError(f"Source '{source.name}' has no view configuration")

        self.sanitize_identifier(view_name)

        select_clause = self._build_select_clause(source)
        from_clause = self._build_from_clause(source)
        join_clause = self._build_join_clause(source)

        return f"CREATE VIEW {view_name} AS SELECT {select_clause} FROM {from_clause}{join_clause}"

    def _build_select_clause(self, source: SourceConfig) -> str:
        """
        Build the SELECT clause for a view.

        Args:
            source: Source configuration

        Returns:
            SELECT clause (without the SELECT keyword)
        """
        view_config = source.view
        select_parts = []

        for select_item in view_config.select:
            column_ref = select_item.column.sql
            if select_item.alias:
                column_ref += f" AS {select_item.alias}"
            select_parts.append(column_ref)

        return self.format_column_list(select_parts)

    def _build_from_clause(self, source: SourceConfig) -> str:
        """
        Build the FROM clause for a view.

        Args:
            source: Source configuration

        Returns:
            FROM clause (without the FROM keyword)
        """
        return source.name

    def _build_join_clause(self, source: SourceConfig) -> str:
        """
        Build the JOIN clause for a view.

        Args:
            source: Source configuration

        Returns:
            JOIN clause (including leading space), or empty string if no joins
        """
        view_config = source.view

        if not view_config.join:
            return ""

        join_parts = []
        for join_item in view_config.join:
            join_condition = join_item.condition

            if join_condition.is_spatial:
                # Spatial joins are precomputed; join on the stored key column
                condition = build_spatial_equality_condition(join_condition)
            else:
                condition = (
                    f"{join_condition.left.column.sql} = "
                    f"{join_condition.right.column.sql}"
                )

            join_parts.append(f"{join_item.method} {join_item.source} ON {condition}")

        return " " + " ".join(join_parts)
