import warnings
from pathlib import Path
from typing import List, Union

from appdirs import user_data_dir

from geoparser.db.crud.feature import FeatureRepository
from geoparser.db.crud.gazetteer import GazetteerRepository
from geoparser.db.crud.name import NameRepository
from geoparser.db.db import create_db_and_tables, get_session, optimized_writes
from geoparser.db.models.gazetteer import GazetteerCreate
from geoparser.gazetteer.installer.model import GazetteerConfig, SourceConfig
from geoparser.gazetteer.installer.stages.acquisition import AcquisitionStage
from geoparser.gazetteer.installer.stages.indexing import IndexingStage
from geoparser.gazetteer.installer.stages.ingestion import IngestionStage
from geoparser.gazetteer.installer.stages.registration import RegistrationStage
from geoparser.gazetteer.installer.stages.schema import SchemaStage
from geoparser.gazetteer.installer.stages.spatial import SpatialStage
from geoparser.gazetteer.installer.stages.transformation import TransformationStage
from geoparser.gazetteer.installer.stages.view import ViewStage
from geoparser.gazetteer.installer.utils.chunking import CHUNKSIZE
from geoparser.gazetteer.installer.utils.dependency import DependencyResolver
from geoparser.gazetteer.installer.utils.progress import (
    print_gazetteer_header,
    print_gazetteer_summary,
    source_progress,
)

# Suppress geopandas warning about geometry column.
# This warning occurs when loading spatial data where the geometry column
# temporarily contains WKT text before being converted to proper geometries.
warnings.filterwarnings(
    "ignore",
    message="Geometry column does not contain geometry.*",
    category=UserWarning,
)


class GazetteerInstaller:
    """
    Orchestrates the complete gazetteer installation process.

    This class coordinates a pipeline of stages that download, process,
    and load gazetteer data into the database. The pipeline follows a
    clear, linear flow:

    1. Acquisition: Download and extract source files
    2. Schema: Create database tables
    3. Ingestion: Load data into tables
    4. Transformation: Apply derivations (geometries stored as WKT)
    5. Spatial: Precompute spatial joins with GeoPandas
    6. View: Create database views
    7. Indexing: Create database indices
    8. Registration: Register features and names

    Each stage is independent and testable, with well-defined
    responsibilities and interfaces.
    """

    def __init__(self):
        """Initialize the orchestrator."""
        self.dependency_resolver = DependencyResolver()

    def install(
        self,
        config_path: Union[str, Path],
        chunksize: int = CHUNKSIZE,
        keep_downloads: bool = False,
    ) -> None:
        """
        Install a gazetteer from a YAML configuration file.

        Args:
            config_path: Path to the YAML configuration file
            chunksize: Number of records to process at once for chunked operations
            keep_downloads: Whether to keep downloaded files after installation

        Raises:
            Exception: If installation fails at any stage
        """
        # Ensure database tables exist
        create_db_and_tables()

        # Load and validate configuration
        config = GazetteerConfig.from_yaml(config_path)

        # Setup directories
        downloads_dir = self._create_downloads_directory(config.name)

        # Ensure gazetteer record exists in database
        self._ensure_gazetteer_record(config.name)

        # Resolve dependencies and get processing order
        ordered_sources = self.dependency_resolver.resolve(config.sources)

        print_gazetteer_header(config.name)

        # Create pipeline stages
        pipeline = self._create_pipeline(config, downloads_dir, chunksize)

        # Tune connections for throughput while loading the gazetteer data
        with optimized_writes():
            # Execute pipeline for each source
            for source in ordered_sources:
                self._execute_pipeline(source, pipeline)

        feature_count, name_count = self._count_registered_entries(config.name)
        print_gazetteer_summary(feature_count, name_count)

        # Cleanup if requested
        if not keep_downloads:
            pipeline[0].cleanup()  # AcquisitionStage has cleanup method

    def _create_downloads_directory(self, gazetteer_name: str) -> Path:
        """
        Create and return the downloads directory for a gazetteer.

        Args:
            gazetteer_name: Name of the gazetteer

        Returns:
            Path to the downloads directory
        """
        downloads_dir = (
            Path(user_data_dir("geoparser", "")) / "downloads" / gazetteer_name
        )
        downloads_dir.mkdir(parents=True, exist_ok=True)
        return downloads_dir

    def _ensure_gazetteer_record(self, gazetteer_name: str) -> None:
        """
        Ensure a gazetteer record exists in the database.

        Creates a new gazetteer record if it doesn't already exist.
        Reuses existing record if one with the same name is found.

        Args:
            gazetteer_name: Name of the gazetteer
        """
        with get_session() as session:
            # Check if gazetteer already exists
            gazetteer_record = GazetteerRepository.get_by_name(session, gazetteer_name)

            # Create new gazetteer record only if it doesn't exist
            if gazetteer_record is None:
                gazetteer_create = GazetteerCreate(name=gazetteer_name)
                GazetteerRepository.create(session, gazetteer_create)

    def _count_registered_entries(self, gazetteer_name: str) -> tuple[int, int]:
        """
        Count registered features and names for a gazetteer.

        Args:
            gazetteer_name: Name of the gazetteer

        Returns:
            Tuple of (feature_count, name_count)
        """
        with get_session() as session:
            feature_count = FeatureRepository.count_by_gazetteer(
                session, gazetteer_name
            )
            name_count = NameRepository.count_by_gazetteer(session, gazetteer_name)
        return feature_count, name_count

    def _create_pipeline(
        self,
        config: GazetteerConfig,
        downloads_dir: Path,
        chunksize: int,
    ) -> List:
        """
        Create the pipeline of stages.

        Args:
            config: Gazetteer configuration
            downloads_dir: Directory for downloaded files
            chunksize: Number of records to process at once

        Returns:
            List of pipeline stages in execution order
        """
        source_map = {source.name: source for source in config.sources}

        return [
            AcquisitionStage(downloads_dir),
            SchemaStage(),
            IngestionStage(chunksize),
            TransformationStage(chunksize),
            SpatialStage(source_map),
            ViewStage(),
            IndexingStage(),
            RegistrationStage(config.name, chunksize),
        ]

    def _execute_pipeline(self, source: SourceConfig, pipeline: List) -> None:
        """
        Execute the complete pipeline for a single source.

        Args:
            source: Source configuration to process
            pipeline: List of pipeline stages
        """
        # Context is shared across all stages for this source
        context = {}

        # Group all of this source's progress bars under a single source-level
        # bar that tracks how many pipeline steps have completed.
        with source_progress(source.name, total_steps=len(pipeline)) as progress:
            # Execute each stage in sequence
            for stage in pipeline:
                stage.execute(source, context)
                progress.advance_step()
