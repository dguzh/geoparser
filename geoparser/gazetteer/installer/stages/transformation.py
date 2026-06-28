from typing import Any, Dict

import sqlalchemy as sa

from geoparser.db.db import get_connection
from geoparser.gazetteer.installer.model import SourceConfig
from geoparser.gazetteer.installer.queries.dml import TransformationBuilder
from geoparser.gazetteer.installer.stages.base import Stage
from geoparser.gazetteer.installer.utils.chunking import (
    CHUNKSIZE,
    count_rows,
    iter_rowid_ranges,
)
from geoparser.gazetteer.installer.utils.progress import create_progress_bar


class TransformationStage(Stage):
    """
    Applies data transformations.

    This stage computes derived columns using SQL expressions. Geometry
    derivations produce WKT text directly into the geometry column. Each
    derivation is applied in rowid-bounded chunks to keep the working set
    small instead of rewriting the whole table in one statement.
    """

    def __init__(self, chunksize: int = CHUNKSIZE):
        """
        Initialize the transformation stage with query builders.

        Args:
            chunksize: Number of rows to process at once for chunked operations
        """
        super().__init__(
            name="Transformation",
            description="Apply derivations",
        )
        self.chunksize = chunksize
        self.transformation_builder = TransformationBuilder()

    def execute(self, source: SourceConfig, context: Dict[str, Any]) -> None:
        """
        Apply transformations for a source.

        Args:
            source: Source configuration
            context: Shared context (must contain 'table_name')
        """
        table_name = context["table_name"]

        self._apply_derivations(source, table_name)

    def _apply_derivations(self, source: SourceConfig, table_name: str) -> None:
        """
        Compute derived columns using SQL expressions.

        Geometry derivations (e.g. building a POINT from longitude/latitude)
        produce WKT text stored directly in the geometry column.

        Args:
            source: Source configuration
            table_name: Name of the table
        """
        if not source.attributes.derived:
            return

        with get_connection() as connection:
            total_rows = count_rows(connection, table_name)

            for attr in source.attributes.derived:
                # Apply the derivation in rowid-bounded chunks, tracking progress
                # by the number of rows processed
                with create_progress_bar(
                    total_rows,
                    f"Deriving {table_name}.{attr.name}",
                    "rows",
                ) as pbar:
                    for rowid_start, rowid_end in iter_rowid_ranges(
                        total_rows, self.chunksize
                    ):
                        update_sql = (
                            self.transformation_builder.build_derivation_update(
                                table_name,
                                attr.name,
                                attr.expression,
                                rowid_start,
                                rowid_end,
                            )
                        )
                        connection.execute(sa.text(update_sql))
                        connection.commit()
                        pbar.update(rowid_end - rowid_start + 1)
