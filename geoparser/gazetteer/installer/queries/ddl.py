from typing import List

from geoparser.gazetteer.installer.queries.base import QueryBuilder
from geoparser.gazetteer.installer.queries.spatial import SpatialOptimizer
from geoparser.gazetteer.model import DataType, SourceConfig


class TableBuilder(QueryBuilder):
    """
    Builds CREATE TABLE statements for gazetteer sources.

    This builder creates table schemas based on source configurations,
    handling both regular columns and geometry columns (which require
    special handling in SpatiaLite).
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

    def build_add_geometry_column(
        self,
        table_name: str,
        column_name: str,
        srid: int,
        geometry_type: str = "GEOMETRY",
        dimension: str = "XY",
    ) -> str:
        """
        Build an AddGeometryColumn statement for SpatiaLite.

        Args:
            table_name: Name of the table
            column_name: Name of the geometry column
            srid: Spatial Reference System Identifier
            geometry_type: Type of geometry (default: "GEOMETRY")
            dimension: Coordinate dimension (default: "XY")

        Returns:
            SQL statement to add a geometry column
        """
        self.sanitize_identifier(table_name)
        self.sanitize_identifier(column_name)

        return (
            f"SELECT AddGeometryColumn('{table_name}', '{column_name}', "
            f"{srid}, '{geometry_type}', '{dimension}')"
        )

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
                    # Geometry columns start as TEXT with _wkt suffix
                    definitions.append(f"{attr.name}_wkt TEXT")
                else:
                    definitions.append(f"{attr.name} {attr.type.value}")

        # Add derived attribute columns
        for attr in source.attributes.derived:
            if attr.type == DataType.GEOMETRY:
                # Geometry columns start as TEXT with _wkt suffix
                definitions.append(f"{attr.name}_wkt TEXT")
            else:
                definitions.append(f"{attr.name} {attr.type.value}")

        return definitions


class ViewBuilder(QueryBuilder):
    """
    Builds CREATE VIEW statements for gazetteer sources.

    This builder creates views that can join multiple sources together
    and select specific columns. It also integrates spatial join
    optimization.
    """

    VIEW_SUFFIX = "_view"

    def __init__(self):
        """Initialize the view builder with a spatial optimizer."""
        self.spatial_optimizer = SpatialOptimizer()

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
            column_ref = f"{select_item.source}.{select_item.column}"
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
            # Optimize spatial join conditions with index hints
            optimized_condition = self.spatial_optimizer.optimize_join_condition(
                join_item.condition
            )
            join_parts.append(
                f"{join_item.type} {join_item.source} ON {optimized_condition}"
            )

        return " " + " ".join(join_parts)
