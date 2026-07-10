"""
Staging of gazetteer source files into transient DuckDB tables.

Tabular sources (those with a ``delimiter``) are loaded with DuckDB's CSV
reader; everything else is loaded with the spatial extension's ``ST_Read``
(shapefiles, GeoPackage, GeoJSON, ...). Staged spatial tables always expose
their geometry column under the name ``geometry``.
"""

import typing as t
from pathlib import Path

import duckdb

from geoparser.gazetteer.config import DataType, SourceConfig
from geoparser.gazetteer.config.schema import GEOMETRY_ATTRIBUTE

GEOMETRY_COLUMN = GEOMETRY_ATTRIBUTE

# Mapping from config attribute types to DuckDB types
_DUCKDB_TYPES = {
    DataType.TEXT: "VARCHAR",
    DataType.INTEGER: "BIGINT",
    DataType.REAL: "DOUBLE",
}


def quote_identifier(name: str) -> str:
    """
    Quote an SQL identifier for DuckDB.

    Args:
        name: Identifier to quote

    Returns:
        Double-quoted identifier with embedded quotes escaped
    """
    escaped = name.replace('"', '""')
    return f'"{escaped}"'


def quote_literal(value: str) -> str:
    """
    Quote a string literal for SQL.

    Args:
        value: String value to quote

    Returns:
        Single-quoted string literal with embedded quotes escaped
    """
    escaped = value.replace("'", "''")
    return f"'{escaped}'"


class Stager:
    """Loads input files into staging tables of a DuckDB connection."""

    def __init__(self, connection: duckdb.DuckDBPyConnection):
        """
        Initialize the stager.

        Args:
            connection: DuckDB connection holding the staging tables
        """
        self.connection = connection

    def stage(self, source_config: SourceConfig, file_path: Path) -> int:
        """
        Load a source file into a staging table named after the source.

        Args:
            source_config: Source configuration
            file_path: Path to the resolved source file

        Returns:
            Number of staged rows
        """
        if source_config.is_tabular:
            self._stage_tabular(source_config, file_path)
        else:
            self._stage_spatial(source_config, file_path)
        table = quote_identifier(source_config.name)
        return self.connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]

    def columns(self, table_name: str) -> t.List[str]:
        """
        Return the column names of a staged table.

        Args:
            table_name: Name of the staging table

        Returns:
            List of column names
        """
        rows = self.connection.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = ? ORDER BY ordinal_position",
            [table_name],
        ).fetchall()
        return [row[0] for row in rows]

    def _stage_tabular(self, source_config: SourceConfig, file_path: Path) -> None:
        """Load a delimited text file via DuckDB's CSV reader."""
        options = [
            f"delim={quote_literal(source_config.delimiter)}",
            f"skip={source_config.skip_rows}",
            "header=false",
            "null_padding=true",
        ]
        quote = source_config.quote if source_config.quote is not None else '"'
        options.append(f"quote={quote_literal(quote)}")
        if not quote:
            options.append("escape=''")

        column_spec = ", ".join(
            f"{quote_literal(attribute.name)}: "
            f"{quote_literal(_DUCKDB_TYPES[attribute.type])}"
            for attribute in source_config.data_attributes
        )
        options.append(f"columns={{{column_spec}}}")

        table = quote_identifier(source_config.name)
        self.connection.execute(
            f"CREATE OR REPLACE TABLE {table} AS "
            f"SELECT * FROM read_csv({quote_literal(str(file_path))}, "
            f"{', '.join(options)})"
        )

    def _stage_spatial(self, source_config: SourceConfig, file_path: Path) -> None:
        """
        Load a spatial file via ST_Read, projected onto its declared attributes.

        The geometry column is normalized to ``geometry`` and the non-geometry
        attributes are cast to their declared types, so the staged table has
        exactly the schema the config declares (mirroring tabular sources).
        """
        raw = quote_identifier(f"__raw_{source_config.name}")
        self.connection.execute(
            f"CREATE OR REPLACE TABLE {raw} AS "
            f"SELECT * FROM ST_Read({quote_literal(str(file_path))})"
        )
        # Geometry types may carry a CRS parameter, e.g. GEOMETRY('EPSG:4326')
        geometry_columns = [
            row[0]
            for row in self.connection.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = ? AND data_type LIKE 'GEOMETRY%'",
                [f"__raw_{source_config.name}"],
            ).fetchall()
        ]
        if not geometry_columns:
            raise ValueError(
                f"Source '{source_config.name}': no geometry column found in "
                f"{file_path}"
            )
        if len(geometry_columns) > 1:
            raise ValueError(
                f"Source '{source_config.name}': multiple geometry columns found "
                f"in {file_path}: {', '.join(geometry_columns)}"
            )
        if geometry_columns[0] != GEOMETRY_COLUMN:
            self.connection.execute(
                f"ALTER TABLE {raw} RENAME COLUMN "
                f"{quote_identifier(geometry_columns[0])} TO "
                f"{quote_identifier(GEOMETRY_COLUMN)}"
            )

        select_parts = []
        for attribute in source_config.attributes:
            column = quote_identifier(attribute.name)
            if attribute.type == DataType.GEOMETRY:
                select_parts.append(column)
            else:
                select_parts.append(
                    f"CAST({column} AS {_DUCKDB_TYPES[attribute.type]}) AS {column}"
                )
        table = quote_identifier(source_config.name)
        self.connection.execute(
            f"CREATE OR REPLACE TABLE {table} AS "
            f"SELECT {', '.join(select_parts)} FROM {raw}"
        )
        self.connection.execute(f"DROP TABLE {raw}")
