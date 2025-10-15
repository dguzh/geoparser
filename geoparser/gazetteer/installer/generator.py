import re

from geoparser.gazetteer.model import SourceConfig


class SQLGenerator:
    """Generates SQL queries for gazetteer installation."""

    # Spatial functions that benefit from spatial index optimization
    SPATIAL_FUNCTIONS = [
        "ST_Within",
        "ST_Intersects",
        "ST_Contains",
        "ST_Overlaps",
        "ST_Touches",
        "ST_Crosses",
        "ST_Disjoint",
        "ST_Equals",
        "ST_Centroid",
    ]
    # SpatiaLite spatial index table name
    SPATIAL_INDEX_TABLE = "SpatialIndex"
    # Column name in spatial index for table reference
    F_TABLE_NAME_COLUMN = "f_table_name"

    def build_view_sql(self, source_config: SourceConfig, view_name: str) -> str:
        """
        Build SQL for creating a view.

        Args:
            source_config: Source configuration with view definition
            view_name: Name for the view

        Returns:
            SQL CREATE VIEW statement
        """
        if source_config.view is None:
            raise ValueError(f"Source '{source_config.name}' has no view configuration")

        view_config = source_config.view

        # Build SELECT clause
        select_parts = []
        for select_item in view_config.select:
            column_ref = f"{select_item.source}.{select_item.column}"
            if select_item.alias:
                column_ref += f" AS {select_item.alias}"
            select_parts.append(column_ref)
        select_clause = ", ".join(select_parts)

        # Build FROM clause
        from_clause = source_config.name

        # Build JOIN clause
        join_clause = ""
        if view_config.join:
            join_parts = []
            for join_item in view_config.join:
                # Optimize spatial join conditions
                optimized_condition = self._optimize_spatial_join_condition(
                    join_item.condition
                )
                join_parts.append(
                    f"{join_item.type} {join_item.source} ON {optimized_condition}"
                )
            join_clause = " " + " ".join(join_parts)

        # Build full SQL
        sql = f"CREATE VIEW {view_name} AS SELECT {select_clause} FROM {from_clause}{join_clause}"

        return sql

    def _optimize_spatial_join_condition(self, condition: str) -> str:
        """
        Transform spatial join conditions into SpatiaLite-optimized expressions.

        Converts expressions like:
            ST_Within(geometry1, table2.geometry2)

        Into:
            table2.rowid IN (SELECT rowid FROM SpatialIndex WHERE f_table_name = 'table2' AND search_frame = geometry1) AND ST_Within(geometry1, table2.geometry2)

        Args:
            condition: Original join condition

        Returns:
            Optimized join condition
        """
        # Try to optimize with ST_Centroid first (more specific pattern)
        if "ST_Centroid" in condition:
            optimized = self._optimize_centroid_spatial_join(condition)
            if optimized != condition:
                return optimized

        # Try standard spatial function optimization
        return self._optimize_standard_spatial_join(condition)

    def _optimize_centroid_spatial_join(self, condition: str) -> str:
        """
        Optimize spatial joins involving ST_Centroid.

        Handles patterns like: ST_Within(ST_Centroid(table1.geom), table2.geom)

        Args:
            condition: Original join condition

        Returns:
            Optimized condition or original if no match found
        """
        # Pattern for ST_Within(ST_Centroid(table1.geom), table2.geom)
        pattern = (
            rf"(ST_\w+)\s*\(\s*ST_Centroid\s*\(\s*([^)]+)\)\s*,\s*(\w+)\.(\w+)\s*\)"
        )
        match = re.search(pattern, condition, re.IGNORECASE)

        if match:
            outer_func = match.group(1)
            geometry1_with_centroid = f"ST_Centroid({match.group(2)})"
            geometry2_table = match.group(3)
            geometry2_column = match.group(4)

            spatial_index_condition = self._build_spatial_index_condition(
                geometry2_table, geometry1_with_centroid
            )
            original_condition = f"{outer_func}({geometry1_with_centroid}, {geometry2_table}.{geometry2_column})"
            optimized_condition = self._combine_index_and_spatial_condition(
                spatial_index_condition, original_condition
            )

            return condition.replace(match.group(0), optimized_condition)

        return condition

    def _optimize_standard_spatial_join(self, condition: str) -> str:
        """
        Optimize standard spatial joins without nesting.

        Handles patterns like: ST_Within(geometry1, table2.geometry2)

        Args:
            condition: Original join condition

        Returns:
            Optimized condition or original if no match found
        """
        for func in self.SPATIAL_FUNCTIONS:
            # Standard pattern without ST_Centroid
            pattern = rf"{func}\s*\(\s*([^,]+),\s*(\w+)\.(\w+)\s*\)"
            match = re.search(pattern, condition, re.IGNORECASE)

            if match:
                geometry1 = match.group(1).strip()
                geometry2_table = match.group(2).strip()
                geometry2_column = match.group(3).strip()

                spatial_index_condition = self._build_spatial_index_condition(
                    geometry2_table, geometry1
                )
                original_condition = (
                    f"{func}({geometry1}, {geometry2_table}.{geometry2_column})"
                )
                optimized_condition = self._combine_index_and_spatial_condition(
                    spatial_index_condition, original_condition
                )

                return condition.replace(match.group(0), optimized_condition)

        # No spatial functions found, return original
        return condition

    def _build_spatial_index_condition(
        self, table_name: str, geometry_expr: str
    ) -> str:
        """
        Build a spatial index lookup condition.

        Args:
            table_name: Name of the table with spatial index
            geometry_expr: Geometry expression to use as search frame

        Returns:
            SQL condition for spatial index lookup
        """
        return (
            f"{table_name}.rowid IN (SELECT rowid FROM {self.SPATIAL_INDEX_TABLE} "
            f"WHERE {self.F_TABLE_NAME_COLUMN} = '{table_name}' AND search_frame = {geometry_expr})"
        )

    def _combine_index_and_spatial_condition(
        self, index_condition: str, spatial_condition: str
    ) -> str:
        """
        Combine spatial index and spatial function conditions.

        Args:
            index_condition: Spatial index lookup condition
            spatial_condition: Original spatial function condition

        Returns:
            Combined condition with both index lookup and spatial check
        """
        return f"{index_condition} AND {spatial_condition}"

    def build_feature_registration_sql(
        self, source_config: SourceConfig, gazetteer_name: str, view_name: str
    ) -> str:
        """
        Build SQL for registering features from a source.

        Args:
            source_config: Source configuration with feature definition
            gazetteer_name: Name of the gazetteer
            view_name: Name of the view to register from (or source name if no view)

        Returns:
            SQL INSERT statement for feature registration
        """
        if source_config.features is None:
            raise ValueError(
                f"Source '{source_config.name}' has no feature configuration"
            )

        # Use first identifier column (currently only support single column)
        identifier_column = source_config.features.identifier[0].column
        source_table = source_config.name
        registration_table = view_name if view_name else source_config.name

        sql = f"""
            INSERT OR IGNORE INTO feature (gazetteer_name, table_name, identifier_name, identifier_value)
            SELECT
                '{gazetteer_name}' as gazetteer_name,
                '{registration_table}' as table_name,
                '{identifier_column}' as identifier_name,
                CAST({identifier_column} AS TEXT) as identifier_value
            FROM {source_table}
            WHERE {identifier_column} IS NOT NULL
            GROUP BY CAST({identifier_column} AS TEXT)
        """

        return sql

    def build_name_registration_sql(
        self,
        source_config: SourceConfig,
        gazetteer_name: str,
        view_name: str,
        name_column: str,
        separator: str = None,
    ) -> str:
        """
        Build SQL for registering names from a source.

        Args:
            source_config: Source configuration
            gazetteer_name: Name of the gazetteer
            view_name: Name of the view (or source name if no view)
            name_column: Column containing names
            separator: Optional separator for splitting names

        Returns:
            SQL INSERT statement for name registration
        """
        if source_config.features is None:
            raise ValueError(
                f"Source '{source_config.name}' has no feature configuration"
            )

        # Use first identifier column (currently only support single column)
        identifier_column = source_config.features.identifier[0].column
        source_table = source_config.name
        registration_table = view_name if view_name else source_config.name

        if separator:
            return self._build_separated_name_sql(
                source_table,
                registration_table,
                identifier_column,
                name_column,
                separator,
                gazetteer_name,
            )
        else:
            return self._build_simple_name_sql(
                source_table,
                registration_table,
                identifier_column,
                name_column,
                gazetteer_name,
            )

    def _build_simple_name_sql(
        self,
        source_table: str,
        registration_table: str,
        identifier_column: str,
        name_column: str,
        gazetteer_name: str,
    ) -> str:
        """
        Build SQL for simple (non-separated) name registration.

        Args:
            source_table: Name of the source table
            registration_table: Name of the table or view to register from
            identifier_column: Column containing feature identifiers
            name_column: Column containing names
            gazetteer_name: Name of the gazetteer

        Returns:
            SQL INSERT statement for name registration
        """
        sql = f"""
            INSERT OR IGNORE INTO name (text, feature_id)
            SELECT
                s.{name_column} as text,
                f.id as feature_id
            FROM {source_table} s
            JOIN feature f ON f.gazetteer_name = '{gazetteer_name}'
                           AND f.table_name = '{registration_table}'
                           AND f.identifier_value = CAST(s.{identifier_column} AS TEXT)
            WHERE s.{name_column} IS NOT NULL AND s.{name_column} != ''
        """
        return sql

    def _build_separated_name_sql(
        self,
        source_table: str,
        registration_table: str,
        identifier_column: str,
        name_column: str,
        separator: str,
        gazetteer_name: str,
    ) -> str:
        """
        Build SQL for separated name registration using recursive CTE.

        Uses a recursive common table expression to split names on a separator
        and register each individual name.

        Args:
            source_table: Name of the source table
            registration_table: Name of the table or view to register from
            identifier_column: Column containing feature identifiers
            name_column: Column containing names
            separator: String to split names on
            gazetteer_name: Name of the gazetteer

        Returns:
            SQL INSERT statement for name registration with name splitting
        """
        sql = f"""
            INSERT OR IGNORE INTO name (text, feature_id)
            WITH RECURSIVE split_names(feature_id, name_value, remaining) AS (
                -- Base case
                SELECT
                    f.id as feature_id,
                    '' as name_value,
                    s.{name_column} || '{separator}' as remaining
                FROM {source_table} s
                JOIN feature f ON f.gazetteer_name = '{gazetteer_name}'
                               AND f.table_name = '{registration_table}'
                               AND f.identifier_value = CAST(s.{identifier_column} AS TEXT)
                WHERE s.{name_column} IS NOT NULL AND s.{name_column} != ''

                UNION ALL

                -- Recursive case
                SELECT
                    feature_id,
                    TRIM(substr(remaining, 1, instr(remaining, '{separator}') - 1)) as name_value,
                    substr(remaining, instr(remaining, '{separator}') + {len(separator)}) as remaining
                FROM split_names
                WHERE remaining != '' AND instr(remaining, '{separator}') > 0
            )
            SELECT
                name_value as text,
                feature_id
            FROM split_names
            WHERE name_value != '' AND name_value IS NOT NULL
        """
        return sql
