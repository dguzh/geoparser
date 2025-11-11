import re
from typing import List


class SpatialOptimizer:
    """
    Optimizes spatial queries by adding spatial index hints.

    SpatiaLite uses R-tree spatial indexes which need to be explicitly
    referenced in queries for optimal performance. This class transforms
    spatial join conditions to include index lookup hints.
    """

    # Spatial functions that benefit from index optimization
    SPATIAL_FUNCTIONS: List[str] = [
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

    # SpatiaLite spatial index table
    SPATIAL_INDEX_TABLE = "SpatialIndex"

    # Column name in spatial index for table reference
    TABLE_NAME_COLUMN = "f_table_name"

    def optimize_join_condition(self, condition: str) -> str:
        """
        Optimize a spatial join condition with index hints.

        Transforms conditions like:
            ST_Within(geometry1, table2.geometry2)

        Into:
            table2.rowid IN (SELECT rowid FROM SpatialIndex
                WHERE f_table_name = 'table2' AND search_frame = geometry1)
            AND ST_Within(geometry1, table2.geometry2)

        Args:
            condition: Original join condition

        Returns:
            Optimized join condition
        """
        # Try centroid optimization first (more specific pattern)
        if "ST_Centroid" in condition:
            optimized = self._optimize_centroid_join(condition)
            if optimized != condition:
                return optimized

        # Try standard spatial function optimization
        return self._optimize_standard_join(condition)

    def _optimize_centroid_join(self, condition: str) -> str:
        """
        Optimize spatial joins involving ST_Centroid.

        Handles patterns like: ST_Within(ST_Centroid(table1.geom), table2.geom)

        Args:
            condition: Original join condition

        Returns:
            Optimized condition or original if no match found
        """
        # Pattern for spatial function with centroid
        pattern = (
            r"(ST_\w+)\s*\(\s*ST_Centroid\s*\(\s*([^)]+)\)\s*,\s*(\w+)\.(\w+)\s*\)"
        )
        match = re.search(pattern, condition, re.IGNORECASE)

        if not match:
            return condition

        outer_func = match.group(1)
        geometry1_expr = f"ST_Centroid({match.group(2)})"
        geometry2_table = match.group(3)
        geometry2_column = match.group(4)

        # Build optimized condition
        index_condition = self._build_index_condition(geometry2_table, geometry1_expr)
        spatial_condition = (
            f"{outer_func}({geometry1_expr}, {geometry2_table}.{geometry2_column})"
        )
        combined = f"{index_condition} AND {spatial_condition}"

        return condition.replace(match.group(0), combined)

    def _optimize_standard_join(self, condition: str) -> str:
        """
        Optimize standard spatial joins without nesting.

        Handles patterns like: ST_Within(geometry1, table2.geometry2)

        Args:
            condition: Original join condition

        Returns:
            Optimized condition or original if no match found
        """
        for func in self.SPATIAL_FUNCTIONS:
            # Pattern for standard spatial function
            pattern = rf"{func}\s*\(\s*([^,]+),\s*(\w+)\.(\w+)\s*\)"
            match = re.search(pattern, condition, re.IGNORECASE)

            if match:
                geometry1_expr = match.group(1).strip()
                geometry2_table = match.group(2).strip()
                geometry2_column = match.group(3).strip()

                # Build optimized condition
                index_condition = self._build_index_condition(
                    geometry2_table, geometry1_expr
                )
                spatial_condition = (
                    f"{func}({geometry1_expr}, {geometry2_table}.{geometry2_column})"
                )
                combined = f"{index_condition} AND {spatial_condition}"

                return condition.replace(match.group(0), combined)

        # No spatial functions found, return original
        return condition

    def _build_index_condition(
        self,
        table_name: str,
        geometry_expr: str,
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
            f"{table_name}.rowid IN ("
            f"SELECT rowid FROM {self.SPATIAL_INDEX_TABLE} "
            f"WHERE {self.TABLE_NAME_COLUMN} = '{table_name}' "
            f"AND search_frame = {geometry_expr})"
        )
