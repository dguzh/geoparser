import shutil
import warnings
import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pyogrio
import requests
from appdirs import user_data_dir
from tqdm.auto import tqdm

from geoparser.db.crud.gazetteer import GazetteerRepository
from geoparser.db.db import engine, get_db, get_gazetteer_prefix
from geoparser.gazetteerv2.config import GazetteerConfig, SourceConfig, SourceType

# Suppress pyogrio warning about CSV field separator
warnings.filterwarnings(
    "ignore",
    message="Selecting .* as CSV field separator, but other candidate separator.*",
    category=RuntimeWarning,
)

# Suppress geopandas warning about geometry column
warnings.filterwarnings(
    "ignore",
    message="Geometry column does not contain geometry.*",
    category=UserWarning,
)


class GazetteerInstaller:
    """
    Installer for gazetteer data.

    This class handles downloading, extracting, and loading gazetteer data
    based on a YAML configuration.
    """

    def __init__(self, chunk_size: int = 10000):
        """
        Initialize the gazetteer installer.

        Args:
            chunk_size: Number of records to process at once for chunked operations
        """
        self.chunk_size = chunk_size

    def install(self, config: GazetteerConfig, keep_downloads: bool = False) -> None:
        """
        Install a gazetteer from a configuration.

        Args:
            config: The gazetteer configuration
            keep_downloads: Whether to keep downloaded files after installation
        """
        # Create directory for this gazetteer
        downloads_path = (
            Path(user_data_dir("geoparser", "")) / "downloads" / config.name
        )
        downloads_path.mkdir(parents=True, exist_ok=True)

        for source in config.sources:
            # Download file if necessary
            file_path = self._download_file(source.url, downloads_path)

            # Extract files if necessary
            data_path = self._extract_files(file_path, downloads_path)

            # Load data into SQLite
            table_name = f"{get_gazetteer_prefix(config.name)}{source.id.lower()}"

            # Call appropriate load method based on source type
            if source.type == SourceType.TABULAR:
                self._load_tabular(data_path, table_name, source)

            elif source.type == SourceType.SPATIAL:
                self._load_spatial(data_path, table_name, source)

        # Update gazetteer metadata
        self._update_gazetteer_metadata(config.name)

        # Clean up downloads if requested
        if not keep_downloads:
            self._cleanup_downloads(downloads_path)

    def _download_file(self, url: str, downloads_path: Path) -> Path:
        """
        Download a file if it doesn't exist or has changed size.

        Args:
            url: URL to download from
            downloads_path: Directory to save the file in

        Returns:
            Path to the downloaded file
        """
        # Create the download path
        file_path = downloads_path / Path(url).name

        if file_path.exists():
            # Check if we need to download by comparing file size
            headers = requests.head(url).headers
            remote_size = int(headers.get("content-length", 0))
            local_size = file_path.stat().st_size

            if remote_size == local_size and remote_size != 0:
                return file_path

        # Stream download with progress bar
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            total_size = int(r.headers.get("content-length", 0))

            with open(file_path, "wb") as f:
                with tqdm(
                    total=total_size,
                    unit="B",
                    unit_scale=True,
                    desc=f"Downloading {file_path.name}",
                ) as pbar:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))

        return file_path

    def _extract_files(self, file_path: Path, downloads_path: Path) -> Path:
        """
        Extract all files from a zip archive into a directory.

        For non-zip files, returns the file path itself.
        For zip files, extracts all contents and returns the extraction directory.

        Args:
            file_path: Path to the archive
            downloads_path: Base directory for extraction

        Returns:
            Path to the extracted directory or the original file path
        """
        # If the archive is not a zip file, return it directly
        if not zipfile.is_zipfile(file_path):
            return file_path

        # Create a unique extraction directory for this archive
        data_path = downloads_path / file_path.stem
        data_path.mkdir(exist_ok=True)

        # If the directory has files, assume it's already extracted
        if any(data_path.iterdir()):
            return data_path

        # Extract all files from the archive with a progress bar
        with zipfile.ZipFile(file_path, "r") as zip_ref:
            file_list = zip_ref.infolist()

            for file in tqdm(
                file_list, desc=f"Extracting {file_path.name}", unit="files"
            ):
                zip_ref.extract(file, data_path)

        return data_path

    def _load_tabular(
        self, data_path: Path, table_name: str, source: SourceConfig
    ) -> None:
        """
        Load tabular data into SQLite using chunked processing.

        Args:
            data_path: Path to the file or directory containing the data
            table_name: Name of the table to create
            source: Source configuration
        """
        # For tabular data, we need to find the target file within the directory
        if data_path.is_dir():
            data_path = data_path / source.target

        # Get total row count for progress bar
        total_rows = (
            pyogrio.read_info(f"CSV:{data_path}", encoding="utf-8")["features"]
            - source.skiprows
        )

        # Calculate chunk size based on total rows
        chunk_size = min(self.chunk_size, total_rows)

        # Get column names
        names = [col.name for col in source.columns]

        # Create column data types dictionary
        dtype = {col.name: col.type for col in source.columns}

        # Read and process file in chunks
        chunk_iter = pd.read_table(
            data_path,
            sep=source.separator,
            skiprows=source.skiprows,
            header=None,
            names=names,
            dtype=dtype,
            low_memory=False,
            chunksize=chunk_size,
        )

        # Process chunks with progress tracking
        with tqdm(total=total_rows, desc=f"Loading {source.id}", unit="rows") as pbar:
            # First chunk replaces, others append
            if_exists = "replace"

            for chunk in chunk_iter:
                # Process this chunk and load to database
                self._process_tabular_chunk(chunk, source, table_name, if_exists)

                # After first chunk, append
                if_exists = "append"

                # Update progress bar
                pbar.update(len(chunk))

    def _process_tabular_chunk(
        self, chunk: pd.DataFrame, source: SourceConfig, table_name: str, if_exists: str
    ) -> None:
        """
        Process a chunk of tabular data and load it to the database.

        Args:
            chunk: Chunk of data to process
            source: Source configuration
            table_name: Name of the table to load data into
            if_exists: How to behave if the table already exists
        """
        # Filter columns based on keep flag
        keep_columns = [col.name for col in source.columns if col.keep]
        chunk = chunk[keep_columns]

        # Create geometry if specified
        if source.geometry:
            # Convert to GeoDataFrame with optimized points creation
            chunk = gpd.GeoDataFrame(
                chunk,
                geometry=gpd.points_from_xy(
                    chunk[source.geometry.x].astype(float),
                    chunk[source.geometry.y].astype(float),
                ),
                crs=source.geometry.crs,
            )

            # Convert geometry to WKT format for storage
            chunk["geometry"] = chunk.geometry.to_wkt()

            # Convert back to DataFrame
            chunk = pd.DataFrame(chunk)

        # Load processed chunk to database
        chunk.to_sql(table_name, engine, index=False, if_exists=if_exists)

    def _load_spatial(
        self, data_path: Path, table_name: str, source: SourceConfig
    ) -> None:
        """
        Load spatial data into SQLite using chunked processing.

        Args:
            data_path: Path to the file or directory containing the data
            table_name: Name of the table to create
            source: Source configuration
        """
        # Set up kwargs for reading
        kwargs = {}
        if source.layer:
            kwargs["layer"] = source.layer

        # Get total row count for progress tracking
        total_rows = pyogrio.read_info(data_path, **kwargs)["features"]

        # Calculate chunk size based on total rows
        chunk_size = min(self.chunk_size, total_rows)

        # Process in chunks with progress tracking
        with tqdm(total=total_rows, desc=f"Loading {source.id}", unit="rows") as pbar:
            # First chunk replaces, others append
            if_exists = "replace"

            # Process in chunks using slice
            for start_idx in range(0, total_rows, chunk_size):
                end_idx = min(start_idx + chunk_size, total_rows)
                chunk_slice = slice(start_idx, end_idx)

                # Read this chunk
                chunk_kwargs = kwargs.copy()
                chunk_kwargs["rows"] = chunk_slice

                # Read chunk from file
                chunk = gpd.read_file(data_path, **chunk_kwargs)

                # Process this chunk and load to database
                self._process_spatial_chunk(chunk, source, table_name, if_exists)

                # After first chunk, append
                if_exists = "append"

                # Update progress
                pbar.update(len(chunk))

    def _process_spatial_chunk(
        self,
        chunk: gpd.GeoDataFrame,
        source: SourceConfig,
        table_name: str,
        if_exists: str,
    ) -> None:
        """
        Process a chunk of spatial data and load it to the database.

        Args:
            chunk: GeoDataFrame chunk to process
            source: Source configuration
            table_name: Name of the table to load data into
            if_exists: How to behave if the table already exists
        """
        # Get config column names
        config_cols = [col.name for col in source.columns]

        # Create a simple mapping from column indices to config column names
        # Skip the geometry column if it exists
        chunk_cols = [col for col in chunk.columns if col != "geometry"]
        rename_map = {
            col: config_cols[i]
            for i, col in enumerate(chunk_cols)
            if i < len(config_cols)
        }

        # Rename columns
        chunk = chunk.rename(columns=rename_map)

        # Filter columns based on keep flag, always including geometry
        keep_columns = [col.name for col in source.columns if col.keep]
        if "geometry" in chunk.columns and "geometry" not in keep_columns:
            keep_columns.append("geometry")

        # Keep only the specified columns
        chunk = chunk[keep_columns]

        # Apply column types from config
        for col in source.columns:
            if col.name in chunk.columns:
                chunk[col.name] = chunk[col.name].astype(col.type)

        # Convert geometry to WKT for storage in SQLite
        chunk["geometry"] = chunk.geometry.to_wkt()

        # Convert to DataFrame and load to database
        pd.DataFrame(chunk).to_sql(table_name, engine, index=False, if_exists=if_exists)

    def _update_gazetteer_metadata(self, name: str) -> None:
        """
        Update gazetteer metadata in the database.

        Args:
            name: Name of the gazetteer
        """
        db = next(get_db())

        GazetteerRepository.upsert_by_name(db, name)

    def _cleanup_downloads(self, downloads_path: Path) -> None:
        """
        Clean up downloaded files and extracted contents.

        Args:
            downloads_path: Path to the gazetteer directory to clean up
        """
        if downloads_path.exists():
            shutil.rmtree(downloads_path)
