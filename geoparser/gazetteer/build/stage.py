"""
Staging of gazetteer input files into transient DuckDB tables.

Tabular inputs (those with a ``delimiter``) are loaded with DuckDB's CSV
reader; everything else is loaded with the spatial extension's ``ST_Read``
(shapefiles, GeoPackage, GeoJSON, ...). Staged spatial tables always expose
their geometry column under the name ``geometry``.
"""

import typing as t
from pathlib import Path

import duckdb

from geoparser.gazetteer.config import DataType, InputConfig

GEOMETRY_COLUMN = "geometry"

# Mapping from config column types to DuckDB types
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

    def stage(self, input_config: InputConfig, file_path: Path) -> int:
        """
        Load an input file into a staging table named after the input.

        Args:
            input_config: Input configuration
            file_path: Path to the resolved input file

        Returns:
            Number of staged rows
        """
        if input_config.is_tabular:
            self._stage_tabular(input_config, file_path)
        else:
            self._stage_spatial(input_config, file_path)
        table = quote_identifier(input_config.name)
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

    def _stage_tabular(self, input_config: InputConfig, file_path: Path) -> None:
        """Load a delimited text file via DuckDB's CSV reader."""
        options = [
            f"delim={quote_literal(input_config.delimiter)}",
            f"skip={input_config.skip_rows}",
            "null_padding=true",
        ]
        quote = input_config.quote if input_config.quote is not None else '"'
        options.append(f"quote={quote_literal(quote)}")
        if not quote:
            options.append("escape=''")

        if input_config.columns is not None:
            column_spec = ", ".join(
                f"{quote_literal(column.name)}: "
                f"{quote_literal(_DUCKDB_TYPES[column.type])}"
                for column in input_config.columns
            )
            options.append("header=false")
            options.append(f"columns={{{column_spec}}}")
        else:
            options.append("header=true")

        table = quote_identifier(input_config.name)
        self.connection.execute(
            f"CREATE OR REPLACE TABLE {table} AS "
            f"SELECT * FROM read_csv({quote_literal(str(file_path))}, "
            f"{', '.join(options)})"
        )

    def _stage_spatial(self, input_config: InputConfig, file_path: Path) -> None:
        """Load a spatial file via ST_Read and normalize the geometry column."""
        table = quote_identifier(input_config.name)
        self.connection.execute(
            f"CREATE OR REPLACE TABLE {table} AS "
            f"SELECT * FROM ST_Read({quote_literal(str(file_path))})"
        )
        # Geometry types may carry a CRS parameter, e.g. GEOMETRY('EPSG:4326')
        geometry_columns = [
            row[0]
            for row in self.connection.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = ? AND data_type LIKE 'GEOMETRY%'",
                [input_config.name],
            ).fetchall()
        ]
        if not geometry_columns:
            raise ValueError(
                f"Input '{input_config.name}': no geometry column found in "
                f"{file_path}"
            )
        if len(geometry_columns) > 1:
            raise ValueError(
                f"Input '{input_config.name}': multiple geometry columns found in "
                f"{file_path}: {', '.join(geometry_columns)}"
            )
        if geometry_columns[0] != GEOMETRY_COLUMN:
            self.connection.execute(
                f"ALTER TABLE {table} RENAME COLUMN "
                f"{quote_identifier(geometry_columns[0])} TO "
                f"{quote_identifier(GEOMETRY_COLUMN)}"
            )
