from abc import ABC, abstractmethod
from pathlib import Path

from geoparser.gazetteer.installer.model import SourceConfig


class LoadStrategy(ABC):
    """
    Abstract base class for data loading strategies.

    Load strategies encapsulate the logic for reading different types
    of data files (tabular, spatial) and loading them into database tables.
    This allows the ingestion stage to work with different file formats
    without knowing the implementation details.
    """

    @abstractmethod
    def load(
        self,
        source: SourceConfig,
        file_path: Path,
        table_name: str,
        chunksize: int,
    ) -> None:
        """
        Load data from a file into a database table.

        Args:
            source: Source configuration
            file_path: Path to the file containing the data
            table_name: Name of the database table to load into
            chunksize: Number of records to process at once

        Raises:
            Exception: If loading fails
        """
