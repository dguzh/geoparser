from pathlib import Path
from typing import Dict

import pandas as pd

from geoparser.db.db import get_connection
from geoparser.gazetteer.installer.model import DataType, SourceConfig
from geoparser.gazetteer.installer.strategies.base import LoadStrategy
from geoparser.gazetteer.installer.utils.progress import create_progress_bar


class TabularLoadStrategy(LoadStrategy):
    """
    Strategy for loading tabular data files (CSV, TSV, etc.).

    This strategy uses pandas to efficiently read and process tabular
    data in chunks, converting it to the appropriate data types before
    loading into the database.
    """

    def load(
        self,
        source: SourceConfig,
        file_path: Path,
        table_name: str,
        chunksize: int,
    ) -> None:
        """
        Load tabular data into a database table.

        Args:
            source: Source configuration
            file_path: Path to the tabular file
            table_name: Name of the database table
            chunksize: Number of records to process at once
        """
        total_rows = self._count_rows(file_path, source.skiprows)
        adjusted_chunksize = min(chunksize, total_rows)

        column_names = self._get_column_names(source)
        dtype_mapping = self._get_dtype_mapping(source)

        chunk_iterator = pd.read_table(
            file_path,
            sep=source.separator,
            skiprows=source.skiprows,
            header=None,
            names=column_names,
            dtype=dtype_mapping,
            low_memory=False,
            chunksize=adjusted_chunksize,
        )

        with create_progress_bar(total_rows, f"Loading {source.name}", "rows") as pbar:
            for chunk in chunk_iterator:
                self._process_chunk(source, chunk, table_name)
                pbar.update(len(chunk))

    def _count_rows(self, file_path: Path, skiprows: int) -> int:
        """
        Count the number of data rows in the file.

        Args:
            file_path: Path to the file
            skiprows: Number of rows to skip at the beginning

        Returns:
            Number of data rows
        """
        with open(file_path, "r", encoding="utf-8") as f:
            return sum(1 for _ in f) - skiprows

    def _get_column_names(self, source: SourceConfig) -> list:
        """
        Extract column names from source configuration.

        Args:
            source: Source configuration

        Returns:
            List of column names
        """
        return [attr.name for attr in source.attributes.original]

    def _get_dtype_mapping(self, source: SourceConfig) -> Dict[str, str]:
        """
        Create a mapping from column names to pandas dtypes.

        Args:
            source: Source configuration

        Returns:
            Dictionary mapping column names to pandas dtype strings
        """
        dtype_map = {}

        for attr in source.attributes.original:
            # Skip geometry columns (not in tabular data)
            if attr.type == DataType.GEOMETRY:
                continue

            # Map DataType to pandas dtype
            if attr.type == DataType.TEXT:
                dtype_map[attr.name] = "str"
            elif attr.type == DataType.INTEGER:
                dtype_map[attr.name] = "Int64"  # Nullable integer
            elif attr.type == DataType.REAL:
                dtype_map[attr.name] = "float64"

        return dtype_map

    def _process_chunk(
        self,
        source: SourceConfig,
        chunk: pd.DataFrame,
        table_name: str,
    ) -> None:
        """
        Process a chunk of data and load it into the database.

        Args:
            source: Source configuration
            chunk: DataFrame chunk to process
            table_name: Name of the database table
        """
        # Filter columns based on drop flag
        keep_columns = [
            attr.name for attr in source.attributes.original if not attr.drop
        ]
        chunk = chunk[keep_columns]

        # Load to database
        with get_connection() as connection:
            chunk.to_sql(table_name, connection, index=False, if_exists="append")
