from pathlib import Path
from typing import Optional

import geopandas as gpd
import pandas as pd
import pyogrio

from geoparser.db.db import get_connection
from geoparser.gazetteer.installer.model import DataType, SourceConfig
from geoparser.gazetteer.installer.strategies.base import LoadStrategy
from geoparser.gazetteer.installer.utils.progress import create_progress_bar


class SpatialLoadStrategy(LoadStrategy):
    """
    Strategy for loading spatial data files (Shapefiles, GeoJSON, etc.).

    This strategy uses geopandas to read spatial data, converts geometries
    to WKT format, and loads the data into the database.
    """

    def load(
        self,
        source: SourceConfig,
        file_path: Path,
        table_name: str,
        chunksize: int,
    ) -> None:
        """
        Load spatial data into a database table.

        Args:
            source: Source configuration
            file_path: Path to the spatial file
            table_name: Name of the database table
            chunksize: Number of records to process at once
        """
        total_rows = pyogrio.read_info(file_path)["features"]
        adjusted_chunksize = min(chunksize, total_rows)

        with create_progress_bar(total_rows, f"Loading {source.name}", "rows") as pbar:
            for start_idx in range(0, total_rows, adjusted_chunksize):
                chunk = self._read_chunk(
                    file_path, start_idx, adjusted_chunksize, total_rows
                )
                self._process_chunk(source, chunk, table_name)
                pbar.update(len(chunk))

    def _read_chunk(
        self,
        file_path: Path,
        start_idx: int,
        chunksize: int,
        total_rows: int,
    ) -> gpd.GeoDataFrame:
        """
        Read a chunk of spatial data from the file.

        Args:
            file_path: Path to the spatial file
            start_idx: Starting row index
            chunksize: Number of rows to read
            total_rows: Total number of rows in the file

        Returns:
            GeoDataFrame containing the chunk
        """
        end_idx = min(start_idx + chunksize, total_rows)
        chunk_slice = slice(start_idx, end_idx)

        return gpd.read_file(file_path, rows=chunk_slice)

    def _process_chunk(
        self,
        source: SourceConfig,
        chunk: gpd.GeoDataFrame,
        table_name: str,
    ) -> None:
        """
        Process a chunk of spatial data and load it into the database.

        Args:
            source: Source configuration
            chunk: GeoDataFrame chunk to process
            table_name: Name of the database table
        """
        # Rename columns to match configuration
        chunk = self._rename_columns(chunk, source)

        # Filter columns based on drop flag
        keep_columns = [
            attr.name for attr in source.attributes.original if not attr.drop
        ]
        chunk = chunk[keep_columns]

        # Convert geometry to WKT
        geometry_attr = self._find_geometry_attribute(source)
        if geometry_attr and geometry_attr.name in chunk.columns:
            chunk[f"{geometry_attr.name}_wkt"] = chunk[geometry_attr.name].to_wkt()
            chunk = chunk.drop(columns=[geometry_attr.name])

        # Load to database
        with get_connection() as connection:
            pd.DataFrame(chunk).to_sql(
                table_name, connection, index=False, if_exists="append"
            )

    def _rename_columns(
        self,
        chunk: gpd.GeoDataFrame,
        source: SourceConfig,
    ) -> gpd.GeoDataFrame:
        """
        Rename columns to match source configuration.

        Args:
            chunk: GeoDataFrame to rename
            source: Source configuration

        Returns:
            GeoDataFrame with renamed columns
        """
        chunk_columns = list(chunk.columns)
        config_columns = [attr.name for attr in source.attributes.original]

        rename_map = {
            col: config_columns[i]
            for i, col in enumerate(chunk_columns)
            if i < len(config_columns)
        }

        return chunk.rename(columns=rename_map)

    def _find_geometry_attribute(self, source: SourceConfig) -> Optional[object]:
        """
        Find the geometry attribute in the source configuration.

        Args:
            source: Source configuration

        Returns:
            The geometry attribute object, or None if none exists
        """
        for attr in source.attributes.original:
            if attr.type == DataType.GEOMETRY and not attr.drop:
                return attr
        return None
