from typing import Any, Dict

import sqlalchemy as sa

from geoparser.db.db import get_connection
from geoparser.gazetteer.installer.model import SourceConfig
from geoparser.gazetteer.installer.queries.dml import TransformationBuilder
from geoparser.gazetteer.installer.stages.base import Stage
from geoparser.gazetteer.installer.utils.progress import create_progress_bar


class TransformationStage(Stage):
    """
    Applies data transformations.

    This stage computes derived columns using SQL expressions. Geometry
    derivations produce WKT text directly into the geometry column.
    """

    def __init__(self):
        """Initialize the transformation stage with query builders."""
        super().__init__(
            name="Transformation",
            description="Apply derivations",
        )
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
            for attr in source.attributes.derived:
                update_sql = self.transformation_builder.build_derivation_update(
                    table_name, attr.name, attr.expression
                )

                # Execute with progress tracking
                with create_progress_bar(
                    1,
                    f"Deriving {table_name}.{attr.name}",
                    "column",
                ) as pbar:
                    connection.execute(sa.text(update_sql))
                    pbar.update(1)

            connection.commit()
