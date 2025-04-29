import shutil
import warnings
import zipfile
from pathlib import Path
from typing import Union

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

    def install(
        self, config_path: Union[str, Path], keep_downloads: bool = False
    ) -> None:
        """
        Install a gazetteer from a YAML configuration file.

        Args:
            config_path: Path to the YAML configuration file
            keep_downloads: Whether to keep downloaded files after installation
        """
        # Load gazetteer configuration from YAML
        gazetteer = GazetteerConfig.from_yaml(config_path)

        # Create directory for this gazetteer
        downloads_dir = (
            Path(user_data_dir("geoparser", "")) / "downloads" / gazetteer.name
        )
        downloads_dir.mkdir(parents=True, exist_ok=True)

        for source in gazetteer.sources:
            # Download file if necessary
            download_path = self._download_file(source.url, downloads_dir)

            # Extract file if necessary and get the path to the specific file
            file_path = self._extract_file(source.file, download_path)

            # Call appropriate load method based on source type
            if source.type == SourceType.TABULAR:
                self._load_tabular(file_path, gazetteer, source)
            elif source.type == SourceType.SPATIAL:
                self._load_spatial(file_path, gazetteer, source)

        # Update gazetteer metadata
        self._update_gazetteer_metadata(gazetteer.name)

        # Clean up downloads if requested
        if not keep_downloads:
            self._cleanup_downloads(downloads_dir)

    def _download_file(self, url: str, downloads_dir: Path) -> Path:
        """
        Download a file if it doesn't exist or has changed size.

        Args:
            url: URL to download from
            downloads_dir: Directory to save the file in

        Returns:
            Path to the downloaded file
        """
        # Create the download path
        download_path = downloads_dir / Path(url).name

        if download_path.exists():
            # Check if we need to download by comparing file size
            headers = requests.head(url).headers
            remote_size = int(headers.get("content-length", 0))
            local_size = download_path.stat().st_size

            if remote_size == local_size and remote_size != 0:
                return download_path

        # Stream download with progress bar
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            total_size = int(r.headers.get("content-length", 0))

            with open(download_path, "wb") as f:
                with tqdm(
                    total=total_size,
                    unit="B",
                    unit_scale=True,
                    desc=f"Downloading {download_path.name}",
                ) as pbar:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))

        return download_path

    def _extract_file(self, file: str, download_path: Path) -> Path:
        """
        Extract files from a zip archive and locate the target file.

        For non-zip files, verifies the file exists and returns its path.
        For zip files, extracts contents and returns the path to the target file.

        Args:
            file: The file to locate after extraction
            download_path: Path to the downloaded file

        Returns:
            Path to the target file

        Raises:
            FileNotFoundError: If the target file can't be found
        """
        # If the archive is not a zip file, check if it's the target file
        if not zipfile.is_zipfile(download_path):
            if download_path.name == file:
                return download_path
            else:
                raise FileNotFoundError(f"File '{file}' not found")

        # Create a unique extraction directory for this archive
        extraction_path = download_path.parent / download_path.stem
        extraction_path.mkdir(exist_ok=True)

        # Extract all files from the archive with a progress bar
        with zipfile.ZipFile(download_path, "r") as zip_ref:
            # Calculate total size for progress tracking
            total_size = sum(file.file_size for file in zip_ref.infolist())

            # Create a progress bar based on bytes
            with tqdm(
                total=total_size,
                unit="B",
                unit_scale=True,
                desc=f"Extracting {download_path.name}",
            ) as pbar:
                # Extract files one by one to update progress incrementally
                for zip_info in zip_ref.infolist():
                    zip_ref.extract(zip_info, path=extraction_path)
                    pbar.update(zip_info.file_size)

        # Look for the target file in the extracted files
        for path in extraction_path.glob("**/*"):
            if path.name == file:
                return path

        # Check if the extraction directory itself might be the target
        if extraction_path.name == file:
            return extraction_path

        # If we can't find the target file, raise an error
        raise FileNotFoundError(f"File '{file}' not found")

    def _load_tabular(
        self, file_path: Path, gazetteer: GazetteerConfig, source: SourceConfig
    ) -> None:
        """
        Load tabular data into SQLite using chunked processing.

        Args:
            file_path: Path to the file containing the data
            gazetteer: The gazetteer configuration
            source: Source configuration
        """
        # Generate table name
        table_name = f"{get_gazetteer_prefix(gazetteer.name)}{source.id.lower()}"

        # Get total row count for progress bar
        total_rows = (
            pyogrio.read_info(f"CSV:{file_path}", encoding="utf-8")["features"]
            - source.skiprows
        )

        # Calculate chunk size based on total rows
        chunk_size = min(self.chunk_size, total_rows)

        # Get column names
        names = [col.name for col in source.columns]

        # Read and process file in chunks
        chunk_iter = pd.read_table(
            file_path,
            sep=source.separator,
            skiprows=source.skiprows,
            header=None,
            names=names,
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
        self, file_path: Path, gazetteer: GazetteerConfig, source: SourceConfig
    ) -> None:
        """
        Load spatial data into SQLite using chunked processing.

        Args:
            file_path: Path to the file containing the data
            gazetteer: The gazetteer configuration
            source: Source configuration
        """
        # Generate table name
        table_name = f"{get_gazetteer_prefix(gazetteer.name)}{source.id.lower()}"

        # Set up kwargs for reading
        kwargs = {}
        if source.layer:
            kwargs["layer"] = source.layer

        # Get total row count for progress tracking
        total_rows = pyogrio.read_info(file_path, **kwargs)["features"]

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
                chunk = gpd.read_file(file_path, **chunk_kwargs)

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

    def _cleanup_downloads(self, downloads_dir: Path) -> None:
        """
        Clean up downloaded files and extracted contents.

        Args:
            downloads_dir: Path to the gazetteer directory to clean up
        """
        if downloads_dir.exists():
            shutil.rmtree(downloads_dir)
