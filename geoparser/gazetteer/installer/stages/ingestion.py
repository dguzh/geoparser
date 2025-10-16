from typing import Any, Dict

from geoparser.gazetteer.installer.stages.base import Stage
from geoparser.gazetteer.installer.strategies.spatial import SpatialLoadStrategy
from geoparser.gazetteer.installer.strategies.tabular import TabularLoadStrategy
from geoparser.gazetteer.model import SourceConfig, SourceType


class IngestionStage(Stage):
    """
    Loads data from files into database tables.

    This stage uses the strategy pattern to delegate loading to
    the appropriate strategy based on the source type (tabular vs spatial).
    """

    def __init__(self, chunksize: int = 20000):
        """
        Initialize the ingestion stage.

        Args:
            chunksize: Number of records to process at once
        """
        super().__init__(
            name="Ingestion",
            description="Load data into database tables",
        )
        self.chunksize = chunksize
        self.strategies = {
            SourceType.TABULAR: TabularLoadStrategy(),
            SourceType.SPATIAL: SpatialLoadStrategy(),
        }

    def execute(self, source: SourceConfig, context: Dict[str, Any]) -> None:
        """
        Load data for a source.

        Args:
            source: Source configuration
            context: Shared context (must contain 'file_path' and 'table_name')
        """
        file_path = context["file_path"]
        table_name = context["table_name"]

        strategy = self.strategies[source.type]
        strategy.load(source, file_path, table_name, self.chunksize)
