from geoparser.gazetteer.installer.queries.base import QueryBuilder
from geoparser.gazetteer.model import SourceConfig


class TransformationBuilder(QueryBuilder):
    """
    Builds UPDATE statements for data transformations.

    This builder creates queries for applying derived column calculations
    and converting WKT text to SpatiaLite geometry objects.
    """

    def build_derivation_update(
        self,
        table_name: str,
        column_name: str,
        expression: str,
    ) -> str:
        """
        Build an UPDATE statement to compute a derived column.

        Args:
            table_name: Name of the table
            column_name: Name of the column to update
            expression: SQL expression to compute the value

        Returns:
            SQL UPDATE statement
        """
        self.sanitize_identifier(table_name)
        self.sanitize_identifier(column_name)

        return f"UPDATE {table_name} SET {column_name} = {expression}"

    def build_geometry_update(
        self,
        table_name: str,
        column_name: str,
        srid: int,
    ) -> str:
        """
        Build an UPDATE statement to convert WKT to geometry.

        Args:
            table_name: Name of the table
            column_name: Name of the geometry column
            srid: Spatial Reference System Identifier

        Returns:
            SQL UPDATE statement
        """
        self.sanitize_identifier(table_name)
        self.sanitize_identifier(column_name)

        wkt_column = f"{column_name}_wkt"

        return (
            f"UPDATE {table_name} "
            f"SET {column_name} = GeomFromText({wkt_column}, {srid}) "
            f"WHERE {wkt_column} IS NOT NULL"
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
        gazetteer_name: str,
        registration_table: str,
    ) -> str:
        """
        Build an INSERT statement to register features.

        Args:
            source: Source configuration with feature definition
            gazetteer_name: Name of the gazetteer
            registration_table: Name of table or view to register from

        Returns:
            SQL INSERT statement

        Raises:
            ValueError: If source has no feature configuration
        """
        if source.features is None:
            raise ValueError(f"Source '{source.name}' has no feature configuration")

        # Use first identifier column (currently only support single column)
        identifier_column = source.features.identifier[0].column
        source_table = source.name

        return f"""
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

    def build_name_insert(
        self,
        source: SourceConfig,
        gazetteer_name: str,
        registration_table: str,
        name_column: str,
    ) -> str:
        """
        Build an INSERT statement to register simple names.

        Args:
            source: Source configuration
            gazetteer_name: Name of the gazetteer
            registration_table: Name of table or view to register from
            name_column: Column containing names

        Returns:
            SQL INSERT statement

        Raises:
            ValueError: If source has no feature configuration
        """
        if source.features is None:
            raise ValueError(f"Source '{source.name}' has no feature configuration")

        identifier_column = source.features.identifier[0].column
        source_table = source.name

        return f"""
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

    def build_name_insert_separated(
        self,
        source: SourceConfig,
        gazetteer_name: str,
        registration_table: str,
        name_column: str,
        separator: str,
    ) -> str:
        """
        Build an INSERT statement to register separated names.

        Uses a recursive CTE to split names on a separator and register
        each individual name.

        Args:
            source: Source configuration
            gazetteer_name: Name of the gazetteer
            registration_table: Name of table or view to register from
            name_column: Column containing names
            separator: String to split names on

        Returns:
            SQL INSERT statement

        Raises:
            ValueError: If source has no feature configuration
        """
        if source.features is None:
            raise ValueError(f"Source '{source.name}' has no feature configuration")

        identifier_column = source.features.identifier[0].column
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
