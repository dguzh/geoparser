from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict

import geopandas as gpd
import pandas as pd
import pyogrio
from tqdm.auto import tqdm

from geoparser.db.engine import engine
from geoparser.gazetteer.model import DataType, SourceConfig, SourceType


class LoadStrategy(ABC):
    """Abstract base class for data loading strategies."""

    @abstractmethod
    def load(
        self,
        source_config: SourceConfig,
        file_path: Path,
        table_name: str,
        chunksize: int,
    ) -> None:
        """Load data from file into database table."""


class TabularLoadStrategy(LoadStrategy):
    """Strategy for loading tabular data files."""

    def load(
        self,
        source_config: SourceConfig,
        file_path: Path,
        table_name: str,
        chunksize: int,
    ) -> None:
        """
        Load tabular data into SQLite using chunked processing.

        Args:
            source_config: Source configuration
            file_path: Path to the file containing the data
            table_name: Name of the table to load into
            chunksize: Number of records to process at once
        """
        # Count total rows for progress bar
        with open(file_path, "r", encoding="utf-8") as f:
            total_rows = sum(1 for _ in f) - source_config.skiprows

        # Adjust chunksize
        chunksize = min(chunksize, total_rows)

        # Get column names and dtype mapping (only original attributes)
        names = [attr.name for attr in source_config.attributes.original]
        dtype = self._get_pandas_dtype_mapping(source_config)

        # Read and process file in chunks
        chunk_iter = pd.read_table(
            file_path,
            sep=source_config.separator,
            skiprows=source_config.skiprows,
            header=None,
            names=names,
            dtype=dtype,
            low_memory=False,
            chunksize=chunksize,
        )

        # Process chunks with progress tracking
        with tqdm(
            total=total_rows, desc=f"Loading {source_config.name}", unit="rows"
        ) as pbar:
            for chunk in chunk_iter:
                self._process_chunk(source_config, chunk, table_name)
                pbar.update(len(chunk))

    def _process_chunk(
        self, source_config: SourceConfig, chunk: pd.DataFrame, table_name: str
    ) -> None:
        """Process a chunk of tabular data and load it to the database."""
        # Filter columns based on drop flag
        keep_columns = [
            attr.name for attr in source_config.attributes.original if not attr.drop
        ]
        chunk = chunk[keep_columns]

        # Load to database
        with engine.connect() as connection:
            chunk.to_sql(table_name, connection, index=False, if_exists="append")

    def _get_pandas_dtype_mapping(self, source_config: SourceConfig) -> Dict:
        """Create a mapping from column names to pandas dtypes."""
        dtype_map = {}
        for attr in source_config.attributes.original:
            # Skip geometry columns
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


class SpatialLoadStrategy(LoadStrategy):
    """Strategy for loading spatial data files."""

    def load(
        self,
        source_config: SourceConfig,
        file_path: Path,
        table_name: str,
        chunksize: int,
    ) -> None:
        """
        Load spatial data into SQLite using chunked processing.

        Args:
            source_config: Source configuration
            file_path: Path to the file containing the data
            table_name: Name of the table to load into
            chunksize: Number of records to process at once
        """
        # Set up kwargs for reading
        kwargs = {}
        if source_config.layer:
            kwargs["layer"] = source_config.layer

        # Get total row count
        total_rows = pyogrio.read_info(file_path, **kwargs)["features"]

        # Adjust chunksize
        chunksize = min(chunksize, total_rows)

        # Process in chunks
        with tqdm(
            total=total_rows, desc=f"Loading {source_config.name}", unit="rows"
        ) as pbar:
            for start_idx in range(0, total_rows, chunksize):
                end_idx = min(start_idx + chunksize, total_rows)
                chunk_slice = slice(start_idx, end_idx)

                # Read chunk
                chunk_kwargs = kwargs.copy()
                chunk_kwargs["rows"] = chunk_slice

                chunk = gpd.read_file(file_path, **chunk_kwargs)

                # Process and load chunk
                self._process_chunk(source_config, chunk, table_name)

                pbar.update(len(chunk))

    def _process_chunk(
        self, source_config: SourceConfig, chunk: gpd.GeoDataFrame, table_name: str
    ) -> None:
        """Process a chunk of spatial data and load it to the database."""
        # Rename columns to match configuration
        chunk_cols = list(chunk.columns)
        config_cols = [attr.name for attr in source_config.attributes.original]

        rename_map = {
            col: config_cols[i]
            for i, col in enumerate(chunk_cols)
            if i < len(config_cols)
        }
        chunk = chunk.rename(columns=rename_map)

        # Filter columns based on drop flag
        keep_columns = [
            attr.name for attr in source_config.attributes.original if not attr.drop
        ]
        chunk = chunk[keep_columns]

        # Convert geometry to WKT
        geometry_attr = self._find_geometry_attr(source_config)
        if geometry_attr and geometry_attr.name in chunk.columns:
            chunk[f"{geometry_attr.name}_wkt"] = chunk[geometry_attr.name].to_wkt()
            chunk = chunk.drop(columns=[geometry_attr.name])

        # Load to database
        with engine.connect() as connection:
            pd.DataFrame(chunk).to_sql(
                table_name, connection, index=False, if_exists="append"
            )

    def _find_geometry_attr(self, source_config: SourceConfig):
        """Find the geometry attribute in the source config."""
        for attr in source_config.attributes.original:
            if attr.type == DataType.GEOMETRY and not attr.drop:
                return attr
        return None


class DataLoader:
    """Loads data from files into database tables using appropriate strategies."""

    def __init__(self):
        self.strategies = {
            SourceType.TABULAR: TabularLoadStrategy(),
            SourceType.SPATIAL: SpatialLoadStrategy(),
        }

    def load(
        self,
        source_config: SourceConfig,
        file_path: Path,
        table_name: str,
        chunksize: int,
    ) -> None:
        """
        Load data from a file into the database using the appropriate strategy.

        Args:
            source_config: Source configuration
            file_path: Path to the file containing the data
            table_name: Name of the table to load into
            chunksize: Number of records to process at once
        """
        strategy = self.strategies[source_config.type]
        strategy.load(source_config, file_path, table_name, chunksize)
