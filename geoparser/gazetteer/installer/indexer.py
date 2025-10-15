from typing import List, Tuple

import sqlalchemy as sa
from tqdm.auto import tqdm

from geoparser.db.engine import engine
from geoparser.gazetteer.model import DataType, SourceConfig


class ColumnIndexer:
    """Creates database indices for gazetteer table columns."""

    def create_indices(self, source_config: SourceConfig, table_name: str) -> None:
        """
        Create indices for columns marked with index=True.

        Args:
            source_config: Source configuration
            table_name: Name of the table to create indices for
        """
        # Collect all columns that need indices
        indexed_columns: List[Tuple[str, DataType]] = []

        # Check original attributes
        for attr in source_config.attributes.original:
            if attr.index and not attr.drop:
                indexed_columns.append((attr.name, attr.type))

        # Check derived attributes
        for attr in source_config.attributes.derived:
            if attr.index:
                indexed_columns.append((attr.name, attr.type))

        if not indexed_columns:
            return

        with engine.connect() as connection:
            for column_name, column_type in indexed_columns:
                try:
                    if column_type == DataType.GEOMETRY:
                        # Create spatial index
                        index_sql = f"SELECT CreateSpatialIndex('{table_name}', '{column_name}')"
                    else:
                        # Create B-tree index
                        index_name = self._get_index_name(table_name, column_name)
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
                except sa.exc.DatabaseError as e:
                    # Log error but continue with other indices
                    print(
                        f"Warning: Failed to create index on {table_name}.{column_name}: {e}"
                    )

            connection.commit()

    def _get_index_name(self, table_name: str, column_name: str) -> str:
        """
        Generate a standard index name.

        Args:
            table_name: Name of the table
            column_name: Name of the column

        Returns:
            Index name in the format idx_{table_name}_{column_name}
        """
        return f"idx_{table_name}_{column_name}"
