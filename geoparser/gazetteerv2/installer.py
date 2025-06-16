import shutil
import warnings
import zipfile
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
from geoparser.db.db import engine, get_db
from geoparser.db.models.gazetteer import GazetteerCreate
from geoparser.gazetteerv2.config import (
    DataType,
    FeatureConfig,
    GazetteerConfig,
    SourceConfig,
    SourceType,
    ToponymConfig,
    ViewConfig,
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
        gazetteer_record = self._create_gazetteer_record(gazetteer_config)

        # First pass: Create all base tables and load data
        for source_config in gazetteer_config.sources:
            # Download file if necessary
            download_path = self._download_file(source_config, downloads_dir)

            # Extract file if necessary and get the path to the specific file
            file_path = self._extract_file(source_config, download_path)

            # Create the table with primary keys and get the table name
            table_name = self._create_table(source_config)

            # Load the data from the file
            self._load_file(source_config, file_path, table_name, chunksize)

            # Apply derivations after loading the data
            self._create_derivations(source_config, table_name)

            # Create indices for indexed columns
            self._create_indices(source_config, table_name)

        # Second pass: Create views if configured
        for view_config in gazetteer_config.views:
            self._create_view(view_config)

        # Third pass: Register features if configured
        for feature_config in gazetteer_config.features:
            self._register_features(gazetteer_config, feature_config)

        # Fourth pass: Register toponyms if configured
        for toponym_config in gazetteer_config.toponyms:
            self._register_toponyms(gazetteer_config, toponym_config)

        # Clean up downloads if requested
        if not keep_downloads:
            self._cleanup_downloads(downloads_dir)

    def _create_gazetteer_record(self, gazetteer_config: GazetteerConfig):
        """
        Create a new gazetteer record in the database.
        If records with the same name already exist, they will be deleted first.

        Args:
            gazetteer_config: Gazetteer configuration

        Returns:
            Created Gazetteer object
        """
        db = next(get_db())
        name = gazetteer_config.name

        # Get all existing gazetteers with this name
        existing_gazetteers = GazetteerRepository.get_by_name(db, name)

        # Delete each existing gazetteer
        for gazetteer in existing_gazetteers:
            GazetteerRepository.delete(db, id=gazetteer.id)

        # Create a new gazetteer record
        return GazetteerRepository.create(db, GazetteerCreate(name=name))

    def _download_file(self, source_config: SourceConfig, downloads_dir: Path) -> Path:
        """
        Download a file if it doesn't exist or has changed size.

        Args:
            source_config: Source configuration
            downloads_dir: Directory to save the file in

        Returns:
            Path to the downloaded file
        """
        # Get the URL from source config
        url = source_config.url

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

    def _extract_file(self, source_config: SourceConfig, download_path: Path) -> Path:
        """
        Extract files from a zip archive and locate the target file.

        For non-zip files, verifies the file exists and returns its path.
        For zip files, extracts contents and returns the path to the target file.

        Args:
            source_config: Source configuration
            download_path: Path to the downloaded file

        Returns:
            Path to the target file

        Raises:
            FileNotFoundError: If the target file can't be found
        """
        # Get the target file from source config
        file = source_config.file

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

    def _cleanup_downloads(self, downloads_dir: Path) -> None:
        """
        Clean up downloaded files and extracted contents.

        Args:
            downloads_dir: Path to the gazetteer directory to clean up
        """
        if downloads_dir.exists():
            shutil.rmtree(downloads_dir)

    def _create_table(self, source_config: SourceConfig) -> str:
        """
        Create a table with the appropriate columns and primary keys.

        Args:
            source_config: Source configuration

        Returns:
            The created table name
        """
        table_name = source_config.name

        # Drop the existing table if it exists
        with engine.connect() as connection:
            connection.execute(sa.text(f"DROP TABLE IF EXISTS {table_name}"))
            connection.commit()

        # Build column definitions
        columns = []
        primary_keys = []

        # Add columns for attributes (that aren't dropped)
        for attr in source_config.attributes:
            if not attr.drop:
                columns.append(f"{attr.name} {attr.type.value}")
                if attr.primary:
                    primary_keys.append(attr.name)

        # Add columns for derivations
        for derivation in source_config.derivations:
            columns.append(f"{derivation.name} {derivation.type.value}")

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

        # Dispose the engine to clear connection pool and cached schema information
        engine.dispose()

        return table_name

    def _load_file(
        self,
        source_config: SourceConfig,
        file_path: Path,
        table_name: str,
        chunksize: int,
    ) -> None:
        """
        Load data from a file into the database.

        This is a helper method that calls the appropriate loader based on source type.

        Args:
            source_config: Source configuration
            file_path: Path to the file containing the data
            table_name: Name of the table to load into
            chunksize: Number of records to process at once
        """
        if source_config.type == SourceType.TABULAR:
            self._load_tabular_file(source_config, file_path, table_name, chunksize)
        elif source_config.type == SourceType.SPATIAL:
            self._load_spatial_file(source_config, file_path, table_name, chunksize)

    def _load_tabular_file(
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
        # Get total row count for progress bar using a more reliable method for tabular files
        with open(file_path, "r", encoding="utf-8") as f:
            total_rows = sum(1 for _ in f) - source_config.skiprows

        # Calculate chunk size based on total rows
        chunksize = min(chunksize, total_rows)

        # Get column names and dtype mapping for pandas
        names = [attr.name for attr in source_config.attributes]
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
                self._process_tabular_chunk(source_config, chunk, table_name)

                # Update progress bar
                pbar.update(len(chunk))

    def _process_tabular_chunk(
        self,
        source_config: SourceConfig,
        chunk: pd.DataFrame,
        table_name: str,
    ) -> None:
        """
        Process a chunk of tabular data and load it to the database.

        Args:
            source_config: Source configuration
            chunk: Chunk of data to process
            table_name: Name of the table to load into
        """
        # Filter columns based on drop flag
        keep_columns = [attr.name for attr in source_config.attributes if not attr.drop]
        chunk = chunk[keep_columns]

        # Load processed chunk to database with append strategy
        chunk.to_sql(table_name, engine, index=False, if_exists="append")

    def _load_spatial_file(
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
                self._process_spatial_chunk(source_config, chunk, table_name)

                # Update progress
                pbar.update(len(chunk))

    def _process_spatial_chunk(
        self,
        source_config: SourceConfig,
        chunk: gpd.GeoDataFrame,
        table_name: str,
    ) -> None:
        """
        Process a chunk of spatial data and load it to the database.

        Args:
            source_config: Source configuration
            chunk: GeoDataFrame chunk to process
            table_name: Name of the table to load into
        """
        # Create a simple mapping from column indices to config column names
        # We assume the order matches between the source data and our configuration
        chunk_cols = list(chunk.columns)
        config_cols = [attr.name for attr in source_config.attributes]

        rename_map = {
            col: config_cols[i]
            for i, col in enumerate(chunk_cols)
            if i < len(config_cols)
        }

        # Rename columns
        chunk = chunk.rename(columns=rename_map)

        # Filter columns based on drop flag
        keep_columns = [attr.name for attr in source_config.attributes if not attr.drop]

        # Keep only the specified columns
        chunk = chunk[keep_columns]

        # Convert geometry to WKT for storage in SQLite
        if "geometry" in chunk.columns:
            chunk["geometry"] = chunk.geometry.to_wkt()

        # Convert to DataFrame and load to database
        pd.DataFrame(chunk).to_sql(table_name, engine, index=False, if_exists="append")

    def _create_derivations(self, source_config: SourceConfig, table_name: str) -> None:
        """
        Create derived columns in a table using SQL expressions.

        This is done after all data has been loaded into the table.

        Args:
            source_config: Source configuration
            table_name: Name of the table to create derivations for
        """
        if not source_config.derivations:
            return

        with engine.connect() as connection:
            for derivation in source_config.derivations:
                # Create an UPDATE statement to set the derived column
                update_sql = (
                    f"UPDATE {table_name} "
                    f"SET {derivation.name} = {derivation.expression}"
                )

                # Execute the update with a progress bar
                with tqdm(
                    total=1,
                    desc=f"Deriving {table_name}.{derivation.name}",
                    unit="column",
                ) as pbar:
                    connection.execute(sa.text(update_sql))
                    pbar.update(1)

            # Commit all the updates
            connection.commit()

    def _create_indices(self, source_config: SourceConfig, table_name: str) -> None:
        """
        Create indices for columns marked with index=True.

        Args:
            source_config: Source configuration
            table_name: Name of the table to create indices for
        """
        # Collect all columns that need indices
        indexed_columns: List[str] = []

        # Check regular attributes
        for attr in source_config.attributes:
            if attr.index and not attr.drop:
                indexed_columns.append(attr.name)

        # Check derivations
        for derivation in source_config.derivations:
            if derivation.index:
                indexed_columns.append(derivation.name)

        if not indexed_columns:
            return

        with engine.connect() as connection:
            for column_name in indexed_columns:
                index_name = f"idx_{table_name}_{column_name}"

                # Create index with a progress bar
                with tqdm(
                    total=1,
                    desc=f"Indexing {table_name}.{column_name}",
                    unit="index",
                ) as pbar:
                    # Drop the index if it exists
                    connection.execute(sa.text(f"DROP INDEX IF EXISTS {index_name}"))

                    # Create the index
                    create_index_sql = (
                        f"CREATE INDEX {index_name} ON {table_name}({column_name})"
                    )
                    connection.execute(sa.text(create_index_sql))
                    pbar.update(1)

            # Commit all the index creations
            connection.commit()

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
        for attr in source_config.attributes:
            # Map our DataType to pandas dtype
            if attr.type == DataType.TEXT:
                dtype_map[attr.name] = "str"
            elif attr.type == DataType.INTEGER:
                dtype_map[attr.name] = "Int64"  # Nullable integer type
            elif attr.type == DataType.REAL:
                dtype_map[attr.name] = "float64"
            # BLOB type doesn't have a direct pandas equivalent, will be handled as object

        return dtype_map

    def _create_view(self, view_config: ViewConfig) -> None:
        """
        Create a SQL view based on view configuration.

        Args:
            view_config: View configuration
        """
        view_name = view_config.name

        with tqdm(
            total=1,
            desc=f"Creating {view_config.name}",
            unit="view",
        ) as pbar:
            with engine.connect() as connection:
                # Drop the view if it exists
                connection.execute(sa.text(f"DROP VIEW IF EXISTS {view_name}"))

                # Build the view SQL
                view_sql = self._build_view_sql(view_config)

                # Create the view
                connection.execute(sa.text(view_sql))
                connection.commit()

            # Mark progress as complete
            pbar.update(1)

    def _build_view_sql(self, view_config: ViewConfig) -> str:
        """
        Build SQL for a view based on the view configuration.

        Args:
            view_config: View configuration

        Returns:
            SQL for creating the view
        """
        view_name = view_config.name

        # Build the select clause
        select_clause = ", ".join(view_config.statement.select)

        # Build the from clause - use source names directly
        from_clause = ", ".join(view_config.statement.from_)

        # Build the join clause if specified
        join_clause = ""
        if view_config.statement.join:
            join_clause = " " + " ".join(view_config.statement.join)

        # Build the full SQL
        sql = f"CREATE VIEW {view_name} AS SELECT {select_clause} FROM {from_clause}{join_clause}"

        return sql

    def _register_features(
        self, gazetteer_config: GazetteerConfig, feature_config: FeatureConfig
    ) -> None:
        """
        Register features from a single source and populate the Feature table.

        Uses efficient INSERT INTO ... SELECT for performance with large datasets.

        Args:
            gazetteer_config: Gazetteer configuration
            feature_config: Configuration for this feature source
        """
        source_name = feature_config.table
        identifier_column = feature_config.identifier_column

        with tqdm(
            total=1,
            desc=f"Registering {source_name}.{identifier_column}",
            unit="source",
        ) as pbar:
            with engine.connect() as connection:
                # Build the feature registration SQL
                insert_sql = self._build_feature_sql(gazetteer_config, feature_config)

                connection.execute(sa.text(insert_sql))
                connection.commit()

            pbar.update(1)

    def _build_feature_sql(
        self, gazetteer_config: GazetteerConfig, feature_config: FeatureConfig
    ) -> str:
        """
        Build SQL for registering features from a source.

        Args:
            gazetteer_config: Gazetteer configuration
            feature_config: Feature configuration

        Returns:
            SQL for inserting features into the Feature table
        """
        source_name = feature_config.table
        identifier_column = feature_config.identifier_column
        gazetteer_name = gazetteer_config.name

        # Use INSERT INTO ... SELECT for performance
        # Let SQLite handle autoincrement for the id column
        sql = f"""
            INSERT OR IGNORE INTO feature (gazetteer_name, table_name, identifier_name, identifier_value)
            SELECT 
                '{gazetteer_name}' as gazetteer_name,
                '{source_name}' as table_name,
                '{identifier_column}' as identifier_name,
                CAST({identifier_column} AS TEXT) as identifier_value
            FROM {source_name}
            WHERE {identifier_column} IS NOT NULL
            GROUP BY CAST({identifier_column} AS TEXT)
        """

        return sql

    def _register_toponyms(
        self, gazetteer_config: GazetteerConfig, toponym_config: ToponymConfig
    ) -> None:
        """
        Register toponyms from a single source and populate the Toponym table.

        Uses efficient INSERT INTO ... SELECT for performance with large datasets.

        Args:
            gazetteer_config: Gazetteer configuration
            toponym_config: Configuration for this toponym source
        """
        source_name = toponym_config.table
        identifier_column = toponym_config.identifier_column
        toponym_column = toponym_config.toponym_column

        with tqdm(
            total=1,
            desc=f"Registering {source_name}.{toponym_column}",
            unit="source",
        ) as pbar:
            with engine.connect() as connection:
                # Build the toponym registration SQL
                if toponym_config.separator:
                    insert_sql = self._build_separated_toponym_sql(
                        gazetteer_config, toponym_config
                    )
                else:
                    insert_sql = self._build_simple_toponym_sql(
                        gazetteer_config, toponym_config
                    )

                connection.execute(sa.text(insert_sql))
                connection.commit()

            pbar.update(1)

    def _build_simple_toponym_sql(
        self, gazetteer_config: GazetteerConfig, toponym_config: ToponymConfig
    ) -> str:
        """
        Build SQL for registering simple (non-separated) toponyms from a source.

        Args:
            gazetteer_config: Gazetteer configuration
            toponym_config: Toponym configuration

        Returns:
            SQL for inserting toponyms into the Toponym table
        """
        source_name = toponym_config.table
        identifier_column = toponym_config.identifier_column
        toponym_column = toponym_config.toponym_column
        gazetteer_name = gazetteer_config.name

        # Use INSERT INTO ... SELECT for performance
        # Let SQLite handle autoincrement for the id column
        sql = f"""
            INSERT OR IGNORE INTO toponym (text, feature_id)
            SELECT 
                s.{toponym_column} as text,
                f.id as feature_id
            FROM {source_name} s
            JOIN feature f ON f.gazetteer_name = '{gazetteer_name}' 
                           AND f.identifier_value = CAST(s.{identifier_column} AS TEXT)
            WHERE s.{toponym_column} IS NOT NULL AND s.{toponym_column} != ''
        """

        return sql

    def _build_separated_toponym_sql(
        self, gazetteer_config: GazetteerConfig, toponym_config: ToponymConfig
    ) -> str:
        """
        Build SQL for registering separated toponyms from a source using recursive CTE.

        Args:
            gazetteer_config: Gazetteer configuration
            toponym_config: Toponym configuration

        Returns:
            SQL for inserting toponyms into the Toponym table
        """
        source_name = toponym_config.table
        identifier_column = toponym_config.identifier_column
        toponym_column = toponym_config.toponym_column
        separator = toponym_config.separator
        gazetteer_name = gazetteer_config.name

        # Use recursive CTE to split comma-separated values
        sql = f"""
            INSERT OR IGNORE INTO toponym (text, feature_id)
            WITH RECURSIVE split_toponyms(feature_id, toponym_value, remaining) AS (
                -- Base case: start with the full toponym column
                SELECT 
                    f.id as feature_id,
                    '' as toponym_value,
                    s.{toponym_column} || '{separator}' as remaining
                FROM {source_name} s
                JOIN feature f ON f.gazetteer_name = '{gazetteer_name}' 
                               AND f.identifier_value = CAST(s.{identifier_column} AS TEXT)
                WHERE s.{toponym_column} IS NOT NULL AND s.{toponym_column} != ''
                
                UNION ALL
                
                -- Recursive case: extract next toponym from remaining string
                SELECT 
                    feature_id,
                    TRIM(substr(remaining, 1, instr(remaining, '{separator}') - 1)) as toponym_value,
                    substr(remaining, instr(remaining, '{separator}') + {len(separator)}) as remaining
                FROM split_toponyms 
                WHERE remaining != '' AND instr(remaining, '{separator}') > 0
            )
            SELECT 
                toponym_value as text,
                feature_id
            FROM split_toponyms 
            WHERE toponym_value != '' AND toponym_value IS NOT NULL
        """

        return sql
