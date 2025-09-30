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
from sqlmodel import Session
from tqdm.auto import tqdm

from geoparser.db.crud.gazetteer import GazetteerRepository
from geoparser.db.engine import engine
from geoparser.db.models.gazetteer import GazetteerCreate
from geoparser.gazetteer.config import (
    DataType,
    FeatureConfig,
    GazetteerConfig,
    NameConfig,
    SourceConfig,
    SourceType,
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

            # Convert WKT text to proper SpatiaLite geometries
            self._build_geometry(source_config, table_name)

            # Create indices for indexed columns
            self._create_indices(source_config, table_name)

        # Second pass: Create views if configured
        for view_config in gazetteer_config.views:
            self._create_view(view_config)

        # Third pass: Register features if configured
        for feature_config in gazetteer_config.features:
            self._register_features(gazetteer_config, feature_config)

        # Fourth pass: Register names if configured
        for name_config in gazetteer_config.names:
            self._register_names(gazetteer_config, name_config)

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
        with Session(engine) as db:
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

        # Drop the existing table if it exists using SpatiaLite's proper cleanup function
        # This ensures all SpatiaLite metadata (geometry_columns, spatial indexes, etc.) are cleaned up
        with engine.connect() as connection:
            # Use DropTable() instead of raw DROP TABLE to properly clean up SpatiaLite metadata
            # The third parameter (1) enables permissive mode, so it won't fail if table doesn't exist
            try:
                connection.execute(
                    sa.text(f"SELECT DropTable(NULL, '{table_name}', 1)")
                )
            except Exception:
                # If DropTable fails for any reason, fall back to regular DROP TABLE
                # This can happen if the table exists but isn't a proper SpatiaLite table
                connection.execute(sa.text(f"DROP TABLE IF EXISTS {table_name}"))
            connection.commit()

        # Build column definitions
        columns = []

        # Find geometry column and get its SRID
        geometry_item = self._find_geometry_item(source_config)

        # Add columns for attributes (that aren't dropped)
        for attr in source_config.attributes:
            if not attr.drop:
                if attr.type == DataType.GEOMETRY:
                    # Create geometry columns as TEXT initially with _wkt suffix
                    columns.append(f"{attr.name}_wkt TEXT")
                else:
                    columns.append(f"{attr.name} {attr.type.value}")

        # Add columns for derivations
        for derivation in source_config.derivations:
            if derivation.type == DataType.GEOMETRY:
                # Create geometry derivations as TEXT initially with _wkt suffix
                columns.append(f"{derivation.name}_wkt TEXT")
            else:
                columns.append(f"{derivation.name} {derivation.type.value}")

        # Create the table without primary key constraints
        create_table_sql = f"CREATE TABLE {table_name} ({', '.join(columns)})"

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

        # For geometry columns, keep them as WKT text for now
        # They will be converted to proper geometries later
        with engine.connect() as connection:
            chunk.to_sql(table_name, connection, index=False, if_exists="append")

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

        # Convert geometry to WKT for insertion as text
        geometry_item = self._find_geometry_item(source_config)
        if geometry_item is not None and geometry_item.name in chunk.columns:
            chunk[f"{geometry_item.name}_wkt"] = chunk[geometry_item.name].to_wkt()
            # Remove the original geometry column since we only want the WKT version for now
            chunk = chunk.drop(columns=[geometry_item.name])

        # Convert to regular DataFrame and use pandas to_sql
        with engine.connect() as connection:
            pd.DataFrame(chunk).to_sql(
                table_name, connection, index=False, if_exists="append"
            )

    def _build_geometry(self, source_config: SourceConfig, table_name: str) -> None:
        """
        Convert WKT text in geometry column to proper SpatiaLite geometries.

        This function converts the TEXT geometry column to a proper SpatiaLite
        geometry column with appropriate constraints.

        Args:
            source_config: Source configuration
            table_name: Name of the table to update
        """
        # Find the geometry item (attribute or derivation) to get the SRID
        geometry_item = self._find_geometry_item(source_config)

        if geometry_item is None:
            # No geometry column, nothing to convert
            return

        with engine.connect() as connection:
            # Step 1: Add a new SpatiaLite geometry column with the proper name
            add_geometry_sql = f"SELECT AddGeometryColumn('{table_name}', '{geometry_item.name}', {geometry_item.srid}, 'GEOMETRY', 'XY')"
            connection.execute(sa.text(add_geometry_sql))

            # Step 2: Populate the new geometry column from the WKT text column
            update_sql = (
                f"UPDATE {table_name} "
                f"SET {geometry_item.name} = GeomFromText({geometry_item.name}_wkt, {geometry_item.srid}) "
                f"WHERE {geometry_item.name}_wkt IS NOT NULL"
            )

            # Execute all steps with a progress bar
            with tqdm(
                total=1,
                desc=f"Building {table_name}.{geometry_item.name}",
                unit="column",
            ) as pbar:
                connection.execute(sa.text(update_sql))
                pbar.update(1)

            # Commit all changes
            connection.commit()

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
                # Handle geometry derivations - store as WKT text
                if derivation.type == DataType.GEOMETRY:
                    # For geometry derivations, store the WKT expression as text
                    # (will be converted to proper geometry later in _build_geometry)
                    update_sql = (
                        f"UPDATE {table_name} "
                        f"SET {derivation.name}_wkt = {derivation.expression}"
                    )
                else:
                    # Regular derivation
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
        # Collect all columns that need indices with their types
        indexed_columns: List[tuple] = []

        # Check regular attributes
        for attr in source_config.attributes:
            if attr.index and not attr.drop:
                indexed_columns.append((attr.name, attr.type))

        # Check derivations
        for derivation in source_config.derivations:
            if derivation.index:
                indexed_columns.append((derivation.name, derivation.type))

        if not indexed_columns:
            return

        with engine.connect() as connection:
            for column_name, column_type in indexed_columns:
                if column_type == DataType.GEOMETRY:
                    # Create spatial index for geometry column
                    index_sql = (
                        f"SELECT CreateSpatialIndex('{table_name}', '{column_name}')"
                    )
                else:
                    # Create regular B-tree index for other columns
                    index_name = f"idx_{table_name}_{column_name}"
                    index_sql = (
                        f"CREATE INDEX {index_name} ON {table_name}({column_name})"
                    )

                # Create index with progress bar
                with tqdm(
                    total=1,
                    desc=f"Indexing {table_name}.{column_name}",
                    unit="index",
                ) as pbar:
                    connection.execute(sa.text(index_sql))
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
            # Skip geometry columns - they're handled specially
            if attr.type == DataType.GEOMETRY:
                continue

            # Map our DataType to pandas dtype
            if attr.type == DataType.TEXT:
                dtype_map[attr.name] = "str"
            elif attr.type == DataType.INTEGER:
                dtype_map[attr.name] = "Int64"  # Nullable integer type
            elif attr.type == DataType.REAL:
                dtype_map[attr.name] = "float64"
            # BLOB type doesn't have a direct pandas equivalent, will be handled as object

        return dtype_map

    def _find_geometry_item(self, source_config: SourceConfig):
        """Find the geometry attribute or derivation (if any) in the source config.

        Returns:
            The geometry attribute/derivation object, or None if no geometry column exists
        """
        # Check attributes first
        for attr in source_config.attributes:
            if attr.type == DataType.GEOMETRY and not attr.drop:
                return attr

        # Check derivations
        for deriv in source_config.derivations:
            if deriv.type == DataType.GEOMETRY:
                return deriv

        return None

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

        # Build the select clause from SelectConfig objects
        select_parts = []
        for select_item in view_config.statement.select:
            column_ref = f"{select_item.table}.{select_item.column}"
            if select_item.alias:
                column_ref += f" AS {select_item.alias}"
            select_parts.append(column_ref)
        select_clause = ", ".join(select_parts)

        # Build the from clause from FromConfig object
        from_clause = view_config.statement.from_.table

        # Build the join clause from JoinConfig objects
        join_clause = ""
        if view_config.statement.join:
            join_parts = []
            for join_item in view_config.statement.join:
                # Optimize spatial join conditions for SpatiaLite
                optimized_condition = self._optimize_spatial_join_condition(
                    join_item.condition
                )
                join_parts.append(
                    f"{join_item.type} {join_item.table} ON {optimized_condition}"
                )
            join_clause = " " + " ".join(join_parts)

        # Build the full SQL
        sql = f"CREATE VIEW {view_name} AS SELECT {select_clause} FROM {from_clause}{join_clause}"

        return sql

    def _optimize_spatial_join_condition(self, condition: str) -> str:
        """
        Transform simple spatial join conditions into SpatiaLite-optimized expressions.

        This converts expressions like:
        ST_Within(geometry1, geometry2_table.geometry2_column)

        Into SpatiaLite-optimized expressions like:
        geometry2_table.rowid IN (SELECT rowid FROM SpatialIndex WHERE f_table_name = 'geometry2_table' AND search_frame = geometry1) AND ST_Within(geometry1, geometry2_table.geometry2_column)

        Args:
            condition: The original join condition

        Returns:
            The optimized join condition
        """
        import re

        # Define spatial functions that can benefit from spatial index optimization
        spatial_functions = [
            "ST_Within",
            "ST_Intersects",
            "ST_Contains",
            "ST_Overlaps",
            "ST_Touches",
            "ST_Crosses",
            "ST_Disjoint",
            "ST_Equals",
        ]

        # Pattern to match spatial function calls with two geometry arguments
        # Matches: FUNCTION(geometry1, geometry2_table.geometry2_column)
        for func in spatial_functions:
            pattern = rf"{func}\s*\(\s*([^,]+),\s*(\w+)\.(\w+)\s*\)"
            match = re.search(pattern, condition, re.IGNORECASE)

            if match:
                geometry1 = match.group(1).strip()
                geometry2_table = match.group(2).strip()
                geometry2_column = match.group(3).strip()

                # Build the optimized condition
                spatial_index_condition = (
                    f"{geometry2_table}.rowid IN (SELECT rowid FROM SpatialIndex "
                    f"WHERE f_table_name = '{geometry2_table}' AND search_frame = {geometry1})"
                )

                original_condition = (
                    f"{func}({geometry1}, {geometry2_table}.{geometry2_column})"
                )
                optimized_condition = (
                    f"{spatial_index_condition} AND {original_condition}"
                )

                # Replace the original condition in the full string
                return condition.replace(match.group(0), optimized_condition)

        # If no spatial functions found, return the original condition
        return condition

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
        # Use table for sourcing data (efficient, no spatial joins)
        source_name = feature_config.table
        # Use view if specified, otherwise use table for registration
        table_name = (
            feature_config.view if feature_config.view else feature_config.table
        )
        identifier_column = feature_config.identifier_column
        gazetteer_name = gazetteer_config.name

        # Use INSERT INTO ... SELECT for performance
        # Let SQLite handle autoincrement for the id column
        sql = f"""
            INSERT OR IGNORE INTO feature (gazetteer_name, table_name, identifier_name, identifier_value)
            SELECT 
                '{gazetteer_name}' as gazetteer_name,
                '{table_name}' as table_name,
                '{identifier_column}' as identifier_name,
                CAST({identifier_column} AS TEXT) as identifier_value
            FROM {source_name}
            WHERE {identifier_column} IS NOT NULL
            GROUP BY CAST({identifier_column} AS TEXT)
        """

        return sql

    def _register_names(
        self, gazetteer_config: GazetteerConfig, name_config: NameConfig
    ) -> None:
        """
        Register names from a single source and populate the Name table.

        Uses efficient INSERT INTO ... SELECT for performance with large datasets.

        Args:
            gazetteer_config: Gazetteer configuration
            name_config: Configuration for this name source
        """
        source_name = name_config.table
        identifier_column = name_config.identifier_column
        name_column = name_config.name_column

        with tqdm(
            total=1,
            desc=f"Registering {source_name}.{name_column}",
            unit="source",
        ) as pbar:
            with engine.connect() as connection:
                # Build the name registration SQL
                if name_config.separator:
                    insert_sql = self._build_separated_name_sql(
                        gazetteer_config, name_config
                    )
                else:
                    insert_sql = self._build_simple_name_sql(
                        gazetteer_config, name_config
                    )

                connection.execute(sa.text(insert_sql))
                connection.commit()

            pbar.update(1)

    def _build_simple_name_sql(
        self, gazetteer_config: GazetteerConfig, name_config: NameConfig
    ) -> str:
        """
        Build SQL for registering simple (non-separated) names from a source.

        Args:
            gazetteer_config: Gazetteer configuration
            name_config: Name configuration

        Returns:
            SQL for inserting names into the Name table
        """
        # Use table for sourcing data (efficient, no spatial joins)
        source_name = name_config.table
        # Use view if specified, otherwise use table for feature matching
        table_name = name_config.view if name_config.view else name_config.table
        identifier_column = name_config.identifier_column
        name_column = name_config.name_column
        gazetteer_name = gazetteer_config.name

        # Use INSERT INTO ... SELECT for performance
        # Let SQLite handle autoincrement for the id column
        sql = f"""
            INSERT OR IGNORE INTO name (text, feature_id)
            SELECT 
                s.{name_column} as text,
                f.id as feature_id
            FROM {source_name} s
            JOIN feature f ON f.gazetteer_name = '{gazetteer_name}' 
                           AND f.table_name = '{table_name}'
                           AND f.identifier_value = CAST(s.{identifier_column} AS TEXT)
            WHERE s.{name_column} IS NOT NULL AND s.{name_column} != ''
        """

        return sql

    def _build_separated_name_sql(
        self, gazetteer_config: GazetteerConfig, name_config: NameConfig
    ) -> str:
        """
        Build SQL for registering separated names from a source using recursive CTE.

        Args:
            gazetteer_config: Gazetteer configuration
            name_config: Name configuration

        Returns:
            SQL for inserting names into the Name table
        """
        # Use table for sourcing data (efficient, no spatial joins)
        source_name = name_config.table
        # Use view if specified, otherwise use table for feature matching
        table_name = name_config.view if name_config.view else name_config.table
        identifier_column = name_config.identifier_column
        name_column = name_config.name_column
        separator = name_config.separator
        gazetteer_name = gazetteer_config.name

        # Use recursive CTE to split comma-separated values
        sql = f"""
            INSERT OR IGNORE INTO name (text, feature_id)
            WITH RECURSIVE split_names(feature_id, name_value, remaining) AS (
                -- Base case: start with the full name column
                SELECT 
                    f.id as feature_id,
                    '' as name_value,
                    s.{name_column} || '{separator}' as remaining
                FROM {source_name} s
                JOIN feature f ON f.gazetteer_name = '{gazetteer_name}' 
                               AND f.table_name = '{table_name}'
                               AND f.identifier_value = CAST(s.{identifier_column} AS TEXT)
                WHERE s.{name_column} IS NOT NULL AND s.{name_column} != ''
                
                UNION ALL
                
                -- Recursive case: extract next name from remaining string
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

        return sql
