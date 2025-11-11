from typing import Any, Dict, List, Tuple

import sqlalchemy as sa

from geoparser.db.db import get_connection
from geoparser.gazetteer.installer.model import DataType, SourceConfig
from geoparser.gazetteer.installer.stages.base import Stage
from geoparser.gazetteer.installer.utils.progress import create_progress_bar


class IndexingStage(Stage):
    """
    Creates database indices for optimized queries.

    This stage creates both B-tree indices for regular columns and
    spatial R-tree indices for geometry columns.
    """

    def __init__(self):
        """Initialize the indexing stage."""
        super().__init__(
            name="Indexing",
            description="Create database indices",
        )

    def execute(self, source: SourceConfig, context: Dict[str, Any]) -> None:
        """
        Create indices for a source.

        Args:
            source: Source configuration
            context: Shared context (must contain 'table_name')
        """
        table_name = context["table_name"]
        indexed_columns = self._collect_indexed_columns(source)

        if not indexed_columns:
            return

        self._create_indices(table_name, indexed_columns)

    def _collect_indexed_columns(
        self,
        source: SourceConfig,
    ) -> List[Tuple[str, DataType]]:
        """
        Collect all columns that need indices.

        Args:
            source: Source configuration

        Returns:
            List of (column_name, column_type) tuples
        """
        indexed_columns = []

        # Check original attributes
        for attr in source.attributes.original:
            if attr.index and not attr.drop:
                indexed_columns.append((attr.name, attr.type))

        # Check derived attributes
        for attr in source.attributes.derived:
            if attr.index:
                indexed_columns.append((attr.name, attr.type))

        return indexed_columns

    def _create_indices(
        self,
        table_name: str,
        indexed_columns: List[Tuple[str, DataType]],
    ) -> None:
        """
        Create indices for all indexed columns.

        Args:
            table_name: Name of the table
            indexed_columns: List of (column_name, column_type) tuples
        """
        with get_connection() as connection:
            for column_name, column_type in indexed_columns:
                try:
                    if column_type == DataType.GEOMETRY:
                        self._create_spatial_index(connection, table_name, column_name)
                    else:
                        self._create_btree_index(connection, table_name, column_name)
                except sa.exc.DatabaseError as e:
                    # Log warning but continue with other indices
                    print(
                        f"Warning: Failed to create index on "
                        f"{table_name}.{column_name}: {e}"
                    )

            connection.commit()

    def _create_spatial_index(
        self,
        connection: sa.engine.Connection,
        table_name: str,
        column_name: str,
    ) -> None:
        """
        Create a spatial R-tree index for a geometry column.

        Args:
            connection: Database connection
            table_name: Name of the table
            column_name: Name of the geometry column
        """
        index_sql = f"SELECT CreateSpatialIndex('{table_name}', '{column_name}')"

        with create_progress_bar(
            1,
            f"Indexing {table_name}.{column_name}",
            "index",
        ) as pbar:
            connection.execute(sa.text(index_sql))
            pbar.update(1)

    def _create_btree_index(
        self,
        connection: sa.engine.Connection,
        table_name: str,
        column_name: str,
    ) -> None:
        """
        Create a B-tree index for a regular column.

        Args:
            connection: Database connection
            table_name: Name of the table
            column_name: Name of the column
        """
        index_name = self._generate_index_name(table_name, column_name)
        index_sql = f"CREATE INDEX {index_name} ON {table_name}({column_name})"

        with create_progress_bar(
            1,
            f"Indexing {table_name}.{column_name}",
            "index",
        ) as pbar:
            connection.execute(sa.text(index_sql))
            pbar.update(1)

    def _generate_index_name(self, table_name: str, column_name: str) -> str:
        """
        Generate a standard index name.

        Args:
            table_name: Name of the table
            column_name: Name of the column

        Returns:
            Index name in the format idx_{table_name}_{column_name}
        """
        return f"idx_{table_name}_{column_name}"
