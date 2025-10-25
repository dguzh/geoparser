import warnings
from pathlib import Path
from typing import List, Union

from appdirs import user_data_dir
from sqlmodel import Session

from geoparser.db.crud.gazetteer import GazetteerRepository
from geoparser.db.engine import get_engine
from geoparser.db.models.gazetteer import GazetteerCreate
from geoparser.gazetteer.installer.model import GazetteerConfig, SourceConfig
from geoparser.gazetteer.installer.stages.acquisition import AcquisitionStage
from geoparser.gazetteer.installer.stages.indexing import IndexingStage
from geoparser.gazetteer.installer.stages.ingestion import IngestionStage
from geoparser.gazetteer.installer.stages.registration import RegistrationStage
from geoparser.gazetteer.installer.stages.schema import SchemaStage
from geoparser.gazetteer.installer.stages.transformation import TransformationStage
from geoparser.gazetteer.installer.utils.dependency import DependencyResolver

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
    2. Schema: Create database tables and views
    3. Ingestion: Load data into tables
    4. Transformation: Apply derivations and build geometries
    5. Indexing: Create database indices
    6. Registration: Register features and names

    Each stage is independent and testable, with well-defined
    responsibilities and interfaces.
    """

    def __init__(self):
        """Initialize the orchestrator."""
        self.dependency_resolver = DependencyResolver()

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

        Raises:
            Exception: If installation fails at any stage
        """
        # Load and validate configuration
        config = GazetteerConfig.from_yaml(config_path)

        # Setup directories
        downloads_dir = self._create_downloads_directory(config.name)

        # Ensure gazetteer record exists in database
        self._ensure_gazetteer_record(config.name)

        # Resolve dependencies and get processing order
        ordered_sources = self.dependency_resolver.resolve(config.sources)

        # Create pipeline stages
        pipeline = self._create_pipeline(config.name, downloads_dir, chunksize)

        # Execute pipeline for each source
        for source in ordered_sources:
            self._execute_pipeline(source, pipeline)

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
        with Session(get_engine()) as db:
            # Check if gazetteer already exists
            gazetteer_record = GazetteerRepository.get_by_name(db, gazetteer_name)

            # Create new gazetteer record only if it doesn't exist
            if gazetteer_record is None:
                gazetteer_create = GazetteerCreate(name=gazetteer_name)
                GazetteerRepository.create(db, gazetteer_create)

    def _create_pipeline(
        self,
        gazetteer_name: str,
        downloads_dir: Path,
        chunksize: int,
    ) -> List:
        """
        Create the pipeline of stages.

        Args:
            gazetteer_name: Name of the gazetteer
            downloads_dir: Directory for downloaded files
            chunksize: Number of records to process at once

        Returns:
            List of pipeline stages in execution order
        """
        return [
            AcquisitionStage(downloads_dir),
            SchemaStage(),
            IngestionStage(chunksize),
            TransformationStage(),
            IndexingStage(),
            RegistrationStage(gazetteer_name),
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

        # Execute each stage in sequence
        for stage in pipeline:
            stage.execute(source, context)
