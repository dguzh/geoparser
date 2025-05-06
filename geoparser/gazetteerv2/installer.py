import shutil
import uuid
import warnings
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Union

import geopandas as gpd
import pandas as pd
import pyogrio
import requests
import sqlalchemy as sa
from appdirs import user_data_dir
from tqdm.auto import tqdm

from geoparser.db.crud.gazetteer import GazetteerRepository
from geoparser.db.crud.gazetteer_relationship import GazetteerRelationshipRepository
from geoparser.db.db import engine, get_db, get_gazetteer_prefix
from geoparser.db.models.gazetteer import GazetteerCreate, GazetteerUpdate
from geoparser.db.models.gazetteer_relationship import GazetteerRelationshipCreate
from geoparser.gazetteerv2.config import (
    DataType,
    GazetteerConfig,
    RelationshipConfig,
    SourceConfig,
    SourceType,
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

    def install(
        self,
        config_path: Union[str, Path],
        chunksize: int = 20000,
        keep_downloads: bool = False,
    ) -> None:
        """
        Install a gazetteer from a YAML configuration file.

        Args:
            config_path: Path to the YAML configuration file
            chunksize: Number of records to process at once for chunked operations
            keep_downloads: Whether to keep downloaded files after installation
        """
        # Load gazetteer configuration from YAML
        gazetteer_config = GazetteerConfig.from_yaml(config_path)

        # Create directory for this gazetteer
        downloads_dir = (
            Path(user_data_dir("geoparser", "")) / "downloads" / gazetteer_config.name
        )
        downloads_dir.mkdir(parents=True, exist_ok=True)

        # Create a new gazetteer entry in the database
        gazetteer_record = self._create_gazetteer_record(gazetteer_config.name)

        for source_config in gazetteer_config.sources:
            # Download file if necessary
            download_path = self._download_file(source_config.url, downloads_dir)

            # Extract file if necessary and get the path to the specific file
            file_path = self._extract_file(source_config.file, download_path)

            # Create the table with primary keys and get the table name
            table_name = self._create_table(gazetteer_config.name, source_config)

            # Load the data from the file
            self._load_file(file_path, table_name, source_config, chunksize)

            # Create derived columns
            if source_config.derived_columns:
                self._create_derived_columns(table_name, source_config, chunksize)

        # Create relationship metadata and indexes
        for relationship_config in gazetteer_config.relationships:
            # Get the table names
            local_table_name = self._get_table_name(
                gazetteer_config.name, relationship_config.local_table
            )
            remote_table_name = self._get_table_name(
                gazetteer_config.name, relationship_config.remote_table
            )

            self._create_relationship_record(
                local_table_name,
                remote_table_name,
                relationship_config,
                gazetteer_record.id,
            )
            self._create_relationship_index(
                local_table_name,
                remote_table_name,
                relationship_config,
                gazetteer_config.sources,
            )

        # Update the gazetteer metadata to indicate completion
        self._update_gazetteer_record(gazetteer_record.id)

        # Clean up downloads if requested
        if not keep_downloads:
            self._cleanup_downloads(downloads_dir)

    def _get_table_name(self, gazetteer_name: str, source_name: str) -> str:
        """
        Get the full table name for a source.

        Args:
            gazetteer_name: Name of the gazetteer
            source_name: Name of the source

        Returns:
            Full table name with prefix
        """
        return f"{get_gazetteer_prefix(gazetteer_name)}{source_name.lower()}"

    def _create_gazetteer_record(self, name: str):
        """
        Create a new gazetteer record in the database.

        Args:
            name: Name of the gazetteer

        Returns:
            Created Gazetteer object
        """
        db = next(get_db())
        return GazetteerRepository.create(db, GazetteerCreate(name=name))

    def _update_gazetteer_record(self, gazetteer_id: uuid.UUID):
        """
        Update an existing gazetteer record in the database.

        Args:
            gazetteer_id: ID of the gazetteer to update
        """
        db = next(get_db())
        gazetteer = GazetteerRepository.get(db, gazetteer_id)

        # Explicitly set the current datetime in the modified field
        update_data = GazetteerUpdate(id=gazetteer_id, modified=datetime.utcnow())

        GazetteerRepository.update(db, db_obj=gazetteer, obj_in=update_data)

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
        extraction_dir = download_path.parent / download_path.stem

        # Check if the extraction directory exists
        if extraction_dir.exists():
            # Check if the extraction directory itself is the target file
            if extraction_dir.name == file:
                # Check if the zip file is newer than the extraction directory
                if download_path.stat().st_mtime <= extraction_dir.stat().st_mtime:
                    # File exists and is up to date, return it
                    return extraction_dir
                # Otherwise, we'll need to re-extract

            # Check if the target file already exists in the extraction path
            for path in extraction_dir.glob("**/*"):
                if path.name == file:
                    # Check if the zip file is not newer than the extracted file
                    if download_path.stat().st_mtime <= path.stat().st_mtime:
                        # File exists and is up to date, return it
                        return path
                    # Otherwise, we'll need to re-extract

            # If we reach here, we need to clean up and re-extract
            shutil.rmtree(extraction_dir)

        # Create extraction directory
        extraction_dir.mkdir(exist_ok=True)

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
                    zip_ref.extract(zip_info, path=extraction_dir)
                    pbar.update(zip_info.file_size)

        # Check if the extraction directory itself might be the target
        if extraction_dir.name == file:
            return extraction_dir

        # Otherwise, look for the target file in the extracted files
        for path in extraction_dir.glob("**/*"):
            if path.name == file:
                return path

        # If we can't find the target file, raise an error
        raise FileNotFoundError(f"File '{file}' not found")

    def _create_table(self, gazetteer_name: str, source_config: SourceConfig) -> str:
        """
        Create a table with the appropriate columns and primary keys.

        Args:
            gazetteer_name: Name of the gazetteer
            source_config: Source configuration

        Returns:
            The created table name
        """
        table_name = self._get_table_name(gazetteer_name, source_config.name)

        # Drop the existing table if it exists
        with engine.connect() as connection:
            connection.execute(sa.text(f"DROP TABLE IF EXISTS {table_name}"))
            connection.commit()

        # Build column definitions
        columns = []
        primary_keys = []

        # Add columns for source columns (that aren't dropped)
        for col in source_config.source_columns:
            if not col.drop:
                columns.append(f"{col.name} {col.type.value}")
                if col.primary:
                    primary_keys.append(col.name)

        # If no primary keys defined, don't add a primary key constraint
        pk_clause = ""
        if primary_keys:
            pk_clause = f", PRIMARY KEY ({', '.join(primary_keys)})"

        # Create the table
        create_table_sql = (
            f"CREATE TABLE {table_name} ({', '.join(columns)}{pk_clause})"
        )

        with engine.connect() as connection:
            connection.execute(sa.text(create_table_sql))
            connection.commit()

        return table_name

    def _load_file(
        self,
        file_path: Path,
        table_name: str,
        source_config: SourceConfig,
        chunksize: int,
    ) -> None:
        """
        Load data from a file into the database.

        This is a helper method that calls the appropriate loader based on source type.

        Args:
            file_path: Path to the file containing the data
            table_name: Name of the table to load into
            source_config: Source configuration
            chunksize: Number of records to process at once
        """
        if source_config.type == SourceType.TABULAR:
            self._load_tabular_file(file_path, table_name, source_config, chunksize)
        elif source_config.type == SourceType.SPATIAL:
            self._load_spatial_file(file_path, table_name, source_config, chunksize)

    def _get_pandas_dtype_mapping(self, source_config: SourceConfig) -> Dict:
        """
        Create a mapping from column names to pandas dtypes.

        This ensures pandas reads in data with the correct types,
        especially important for text columns that might otherwise
        be inferred as numeric.

        Args:
            source_config: Source configuration

        Returns:
            Dictionary mapping column names to pandas dtypes
        """
        dtype_map = {}
        for col in source_config.source_columns:
            # Map our DataType to pandas dtype
            if col.type == DataType.TEXT:
                dtype_map[col.name] = "str"
            elif col.type == DataType.INTEGER:
                dtype_map[col.name] = "Int64"  # Nullable integer type
            elif col.type == DataType.REAL:
                dtype_map[col.name] = "float64"
            # BLOB type doesn't have a direct pandas equivalent, will be handled as object

        return dtype_map

    def _load_tabular_file(
        self,
        file_path: Path,
        table_name: str,
        source_config: SourceConfig,
        chunksize: int,
    ) -> None:
        """
        Load tabular data into SQLite using chunked processing.

        Args:
            file_path: Path to the file containing the data
            table_name: Name of the table to load into
            source_config: Source configuration
            chunksize: Number of records to process at once
        """
        # Get total row count for progress bar using a more reliable method for tabular files
        with open(file_path, "r", encoding="utf-8") as f:
            total_rows = sum(1 for _ in f) - source_config.skiprows

        # Calculate chunk size based on total rows
        chunksize = min(chunksize, total_rows)

        # Get column names and dtype mapping for pandas
        names = [col.name for col in source_config.source_columns]
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
                # Process this chunk and load to database
                self._process_tabular_chunk(chunk, table_name, source_config)

                # Update progress bar
                pbar.update(len(chunk))

    def _process_tabular_chunk(
        self, chunk: pd.DataFrame, table_name: str, source_config: SourceConfig
    ) -> None:
        """
        Process a chunk of tabular data and load it to the database.

        Args:
            chunk: Chunk of data to process
            table_name: Name of the table to load into
            source_config: Source configuration
        """
        # Filter columns based on drop flag
        keep_columns = [
            col.name for col in source_config.source_columns if not col.drop
        ]
        chunk = chunk[keep_columns]

        # Load processed chunk to database with append strategy
        chunk.to_sql(table_name, engine, index=False, if_exists="append")

    def _load_spatial_file(
        self,
        file_path: Path,
        table_name: str,
        source_config: SourceConfig,
        chunksize: int,
    ) -> None:
        """
        Load spatial data into SQLite using chunked processing.

        Args:
            file_path: Path to the file containing the data
            table_name: Name of the table to load into
            source_config: Source configuration
            chunksize: Number of records to process at once
        """
        # Set up kwargs for reading
        kwargs = {}
        if source_config.layer:
            kwargs["layer"] = source_config.layer

        # Get total row count for progress tracking
        total_rows = pyogrio.read_info(file_path, **kwargs)["features"]

        # Calculate chunk size based on total rows
        chunksize = min(chunksize, total_rows)

        # Process in chunks with progress tracking
        with tqdm(
            total=total_rows, desc=f"Loading {source_config.name}", unit="rows"
        ) as pbar:
            # Process in chunks using slice
            for start_idx in range(0, total_rows, chunksize):
                end_idx = min(start_idx + chunksize, total_rows)
                chunk_slice = slice(start_idx, end_idx)

                # Read this chunk
                chunk_kwargs = kwargs.copy()
                chunk_kwargs["rows"] = chunk_slice

                # Read chunk from file
                chunk = gpd.read_file(file_path, **chunk_kwargs)

                # Process this chunk and load to database
                self._process_spatial_chunk(chunk, table_name, source_config)

                # Update progress
                pbar.update(len(chunk))

    def _process_spatial_chunk(
        self,
        chunk: gpd.GeoDataFrame,
        table_name: str,
        source_config: SourceConfig,
    ) -> None:
        """
        Process a chunk of spatial data and load it to the database.

        Args:
            chunk: GeoDataFrame chunk to process
            table_name: Name of the table to load into
            source_config: Source configuration
        """
        # Create a simple mapping from column indices to config column names
        # We assume the order matches between the source data and our configuration
        chunk_cols = list(chunk.columns)
        config_cols = [col.name for col in source_config.source_columns]

        rename_map = {
            col: config_cols[i]
            for i, col in enumerate(chunk_cols)
            if i < len(config_cols)
        }

        # Rename columns
        chunk = chunk.rename(columns=rename_map)

        # Filter columns based on drop flag
        keep_columns = [
            col.name for col in source_config.source_columns if not col.drop
        ]

        # Keep only the specified columns
        chunk = chunk[keep_columns]

        # Convert geometry to WKT for storage in SQLite
        if "geometry" in chunk.columns:
            chunk["geometry"] = chunk.geometry.to_wkt()

        # Convert to DataFrame and load to database
        pd.DataFrame(chunk).to_sql(table_name, engine, index=False, if_exists="append")

    def _create_derived_columns(
        self, table_name: str, source_config: SourceConfig, chunksize: int
    ) -> None:
        """
        Create derived columns from SQL expressions.

        Args:
            table_name: Name of the table
            source_config: Source configuration
            chunksize: Number of records to process at once
        """
        # Get row count for progress tracking
        with engine.connect() as connection:
            result = connection.execute(sa.text(f"SELECT COUNT(*) FROM {table_name}"))
            total_rows = result.scalar()

        # No action needed if the table is empty
        if total_rows == 0:
            return

        # For each derived column
        for col_config in source_config.derived_columns:
            # Add column to the table
            with engine.connect() as connection:
                connection.execute(
                    sa.text(
                        f"ALTER TABLE {table_name} ADD COLUMN {col_config.name} "
                        f"{col_config.type.value}"
                    )
                )
                connection.commit()

            # Create progress bar for this column
            with tqdm(
                total=total_rows,
                desc=f"Deriving {source_config.name}.{col_config.name}",
                unit="rows",
            ) as pbar:
                # Process in chunks to keep memory usage low
                for offset in range(0, total_rows, chunksize):
                    limit = min(chunksize, total_rows - offset)
                    end_rowid = offset + limit

                    # Update the chunk
                    with engine.connect() as connection:
                        connection.execute(
                            sa.text(
                                f"""
                                UPDATE {table_name} 
                                SET {col_config.name} = ({col_config.expression})
                                WHERE rowid BETWEEN {offset + 1} AND {end_rowid}
                                """
                            )
                        )
                        connection.commit()

                    # Update progress
                    pbar.update(limit)

    def _create_relationship_record(
        self,
        local_table_name: str,
        remote_table_name: str,
        relationship_config: RelationshipConfig,
        gazetteer_id: uuid.UUID,
    ) -> None:
        """
        Create a single relationship metadata record in the database.

        Args:
            local_table_name: Name of the local table
            remote_table_name: Name of the remote table
            relationship_config: Relationship configuration
            gazetteer_id: ID of the gazetteer in the database
        """
        # Get a database session
        db = next(get_db())

        # Store relationship metadata
        relationship = GazetteerRelationshipCreate(
            gazetteer_id=gazetteer_id,
            local_table=local_table_name,
            local_column=relationship_config.local_column,
            remote_table=remote_table_name,
            remote_column=relationship_config.remote_column,
        )
        GazetteerRelationshipRepository.create(db, relationship)

    def _create_relationship_index(
        self,
        local_table_name: str,
        remote_table_name: str,
        relationship_config: RelationshipConfig,
        source_configs: List[SourceConfig],
    ) -> None:
        """
        Create indexes for a single relationship.

        Args:
            local_table_name: Name of the local table
            remote_table_name: Name of the remote table
            relationship_config: Relationship configuration
            source_configs: List of all source configurations
        """
        # Find the source configurations
        local_source = next(
            s for s in source_configs if s.name == relationship_config.local_table
        )
        remote_source = next(
            s for s in source_configs if s.name == relationship_config.remote_table
        )

        # Check if the local column is already a primary key
        local_is_primary = any(
            col.name == relationship_config.local_column and col.primary
            for col in local_source.source_columns
        )

        # Check if the remote column is already a primary key
        remote_is_primary = any(
            col.name == relationship_config.remote_column and col.primary
            for col in remote_source.source_columns
        )

        # Create index for local column if it's not a primary key
        if not local_is_primary:
            index_name = f"{local_table_name}__{relationship_config.local_column}"
            with tqdm(
                total=1,
                desc=f"Indexing {relationship_config.local_table}.{relationship_config.local_column}",
                unit="index",
            ) as pbar:
                with engine.connect() as connection:
                    connection.execute(
                        sa.text(
                            f"CREATE INDEX IF NOT EXISTS {index_name} ON {local_table_name}({relationship_config.local_column})"
                        )
                    )
                    connection.commit()
                pbar.update(1)

        # Create index for remote column if it's not a primary key
        if not remote_is_primary:
            index_name = f"{remote_table_name}__{relationship_config.remote_column}"
            with tqdm(
                total=1,
                desc=f"Indexing {relationship_config.remote_table}.{relationship_config.remote_column}",
                unit="index",
            ) as pbar:
                with engine.connect() as connection:
                    connection.execute(
                        sa.text(
                            f"CREATE INDEX IF NOT EXISTS {index_name} ON {remote_table_name}({relationship_config.remote_column})"
                        )
                    )
                    connection.commit()
                pbar.update(1)

    def _cleanup_downloads(self, downloads_dir: Path) -> None:
        """
        Clean up downloaded files and extracted contents.

        Args:
            downloads_dir: Path to the gazetteer directory to clean up
        """
        if downloads_dir.exists():
            shutil.rmtree(downloads_dir)
