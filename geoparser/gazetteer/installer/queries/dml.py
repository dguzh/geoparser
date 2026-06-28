from geoparser.gazetteer.installer.model import SourceConfig
from geoparser.gazetteer.installer.queries.base import QueryBuilder


class TransformationBuilder(QueryBuilder):
    """
    Builds UPDATE statements for data transformations.

    This builder creates queries for applying derived column calculations,
    including geometries that are stored as WKT text.
    """

    def build_derivation_update(
        self,
        table_name: str,
        column_name: str,
        expression: str,
        rowid_start: int,
        rowid_end: int,
    ) -> str:
        """
        Build an UPDATE statement to compute a derived column for a rowid range.

        Args:
            table_name: Name of the table
            column_name: Name of the column to update
            expression: SQL expression to compute the value
            rowid_start: Inclusive lower rowid bound of the chunk
            rowid_end: Inclusive upper rowid bound of the chunk

        Returns:
            SQL UPDATE statement
        """
        self.sanitize_identifier(table_name)
        self.sanitize_identifier(column_name)

        return (
            f"UPDATE {table_name} SET {column_name} = {expression} "
            f"WHERE rowid BETWEEN {rowid_start} AND {rowid_end}"
        )


class FeatureRegistrationBuilder(QueryBuilder):
    """
    Builds INSERT statements for feature and name registration.

    This builder creates queries to register features from gazetteer
    sources into the main feature and name tables.
    """

    def build_feature_insert(
        self,
        source: SourceConfig,
        source_id: int,
        rowid_start: int,
        rowid_end: int,
    ) -> str:
        """
        Build an INSERT statement to register features for a rowid range.

        Args:
            source: Source configuration with feature definition
            source_id: ID of the source record
            rowid_start: Inclusive lower rowid bound of the chunk
            rowid_end: Inclusive upper rowid bound of the chunk

        Returns:
            SQL INSERT statement

        Raises:
            ValueError: If source has no feature configuration
        """
        if source.features is None:
            raise ValueError(f"Source '{source.name}' has no feature configuration")

        # Use first identifier column (currently only support single column)
        identifier_column = source.features.identifier[0].column.column
        source_table = source.name

        return f"""
            INSERT OR IGNORE INTO feature (source_id, location_id_value)
            SELECT
                {source_id} as source_id,
                CAST({identifier_column} AS TEXT) as location_id_value
            FROM {source_table}
            WHERE {identifier_column} IS NOT NULL
              AND {source_table}.rowid BETWEEN {rowid_start} AND {rowid_end}
            GROUP BY CAST({identifier_column} AS TEXT)
        """

    def build_name_insert(
        self,
        source: SourceConfig,
        source_id: int,
        name_column: str,
        rowid_start: int,
        rowid_end: int,
    ) -> str:
        """
        Build an INSERT statement to register simple names for a rowid range.

        Args:
            source: Source configuration
            source_id: ID of the source record
            name_column: Column containing names
            rowid_start: Inclusive lower rowid bound of the chunk
            rowid_end: Inclusive upper rowid bound of the chunk

        Returns:
            SQL INSERT statement

        Raises:
            ValueError: If source has no feature configuration
        """
        if source.features is None:
            raise ValueError(f"Source '{source.name}' has no feature configuration")

        identifier_column = source.features.identifier[0].column.column
        source_table = source.name

        return f"""
            INSERT OR IGNORE INTO name (text, feature_id)
            SELECT
                s.{name_column} as text,
                f.id as feature_id
            FROM {source_table} s
            JOIN feature f ON f.source_id = {source_id}
                           AND f.location_id_value = CAST(s.{identifier_column} AS TEXT)
            WHERE s.{name_column} IS NOT NULL AND s.{name_column} != ''
              AND s.rowid BETWEEN {rowid_start} AND {rowid_end}
        """

    def build_name_insert_separated(
        self,
        source: SourceConfig,
        source_id: int,
        name_column: str,
        separator: str,
        rowid_start: int,
        rowid_end: int,
    ) -> str:
        """
        Build an INSERT statement to register separated names for a rowid range.

        Uses a recursive CTE to split names on a separator and register
        each individual name. Restricting the base case to a rowid range keeps
        the recursion bounded to the rows in the current chunk.

        Args:
            source: Source configuration
            source_id: ID of the source record
            name_column: Column containing names
            separator: String to split names on
            rowid_start: Inclusive lower rowid bound of the chunk
            rowid_end: Inclusive upper rowid bound of the chunk

        Returns:
            SQL INSERT statement

        Raises:
            ValueError: If source has no feature configuration
        """
        if source.features is None:
            raise ValueError(f"Source '{source.name}' has no feature configuration")

        identifier_column = source.features.identifier[0].column.column
        source_table = source.name

        return f"""
            INSERT OR IGNORE INTO name (text, feature_id)
            WITH RECURSIVE split_names(feature_id, name_value, remaining) AS (
                -- Base case
                SELECT
                    f.id as feature_id,
                    '' as name_value,
                    s.{name_column} || '{separator}' as remaining
                FROM {source_table} s
                JOIN feature f ON f.source_id = {source_id}
                               AND f.location_id_value = CAST(s.{identifier_column} AS TEXT)
                WHERE s.{name_column} IS NOT NULL AND s.{name_column} != ''
                  AND s.rowid BETWEEN {rowid_start} AND {rowid_end}

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
