import warnings
from pathlib import Path
from typing import Union

from appdirs import user_data_dir
from sqlmodel import Session

from geoparser.db.crud.gazetteer import GazetteerRepository
from geoparser.db.engine import engine
from geoparser.db.models.gazetteer import GazetteerCreate
from geoparser.gazetteer.installer.builder import SchemaBuilder
from geoparser.gazetteer.installer.downloader import DataDownloader
from geoparser.gazetteer.installer.indexer import ColumnIndexer
from geoparser.gazetteer.installer.loader import DataLoader
from geoparser.gazetteer.installer.registrar import FeatureRegistrar
from geoparser.gazetteer.installer.resolver import DependencyResolver
from geoparser.gazetteer.installer.transformer import DataTransformer
from geoparser.gazetteer.model import GazetteerConfig

# Suppress geopandas warning about geometry column
warnings.filterwarnings(
    "ignore",
    message="Geometry column does not contain geometry.*",
    category=UserWarning,
)


class GazetteerInstaller:
    """
    Orchestrates gazetteer installation workflow.

    This class coordinates the installation of gazetteer data by delegating
    tasks to specialized components.
    """

    def __init__(self):
        self.downloader = DataDownloader()
        self.builder = SchemaBuilder()
        self.loader = DataLoader()
        self.transformer = DataTransformer()
        self.indexer = ColumnIndexer()
        self.registrar = FeatureRegistrar()
        self.resolver = DependencyResolver()

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
        # Load configuration
        config = GazetteerConfig.from_yaml(config_path)

        # Setup directories
        downloads_dir = self._setup_directory(config)

        # Create gazetteer record in database
        gazetteer_record = self._create_gazetteer_record(config)

        # Resolve source dependencies and get processing order
        ordered_sources = self.resolver.resolve(config.sources)

        # Process each source in dependency order
        for source in ordered_sources:
            self._process_source(source, config, downloads_dir, chunksize)

        # Cleanup downloads if requested
        if not keep_downloads:
            self.downloader.cleanup(downloads_dir)

    def _setup_directory(self, config: GazetteerConfig) -> Path:
        """Create and return the downloads directory for this gazetteer."""
        downloads_dir = Path(user_data_dir("geoparser", "")) / "downloads" / config.name
        downloads_dir.mkdir(parents=True, exist_ok=True)
        return downloads_dir

    def _create_gazetteer_record(self, config: GazetteerConfig):
        """
        Create a new gazetteer record in the database.

        If records with the same name already exist, they will be deleted first.

        Args:
            config: Gazetteer configuration

        Returns:
            Created Gazetteer object
        """
        with Session(engine) as db:
            name = config.name

            # Get all existing gazetteers with this name
            existing_gazetteers = GazetteerRepository.get_by_name(db, name)

            # Delete each existing gazetteer
            for gazetteer in existing_gazetteers:
                GazetteerRepository.delete(db, id=gazetteer.id)

            # Create a new gazetteer record
            return GazetteerRepository.create(db, GazetteerCreate(name=name))

    def _process_source(
        self, source, config: GazetteerConfig, downloads_dir: Path, chunksize: int
    ) -> None:
        """
        Process a single source through the full installation pipeline.

        Args:
            source: Source configuration
            config: Gazetteer configuration
            downloads_dir: Directory for downloaded files
            chunksize: Number of records to process at once
        """
        # Download and extract
        file_path = self.downloader.download_and_extract(source, downloads_dir)

        # Build schema and load data
        table_name = self.builder.create_table(source)
        self.loader.load(source, file_path, table_name, chunksize)

        # Transform data
        self.transformer.apply_derivations(source, table_name)
        self.transformer.build_geometry(source, table_name)

        # Create indices
        self.indexer.create_indices(source, table_name)

        # Create view if configured
        view_name = None
        if source.view:
            view_name = self.builder.create_view(source)

        # Register features and names if configured
        if source.features:
            self.registrar.register(source, config.name, view_name)
