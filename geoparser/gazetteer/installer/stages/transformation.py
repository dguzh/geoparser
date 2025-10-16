from typing import Any, Dict, Optional

import sqlalchemy as sa

from geoparser.db.engine import engine
from geoparser.gazetteer.installer.model import DataType, SourceConfig
from geoparser.gazetteer.installer.queries.ddl import TableBuilder
from geoparser.gazetteer.installer.queries.dml import TransformationBuilder
from geoparser.gazetteer.installer.stages.base import Stage
from geoparser.gazetteer.installer.utils.progress import create_progress_bar


class TransformationStage(Stage):
    """
    Applies data transformations.

    This stage computes derived columns using SQL expressions and
    converts WKT text to proper SpatiaLite geometry objects.
    """

    # SpatiaLite geometry type and dimension constants
    GEOMETRY_TYPE = "GEOMETRY"
    COORDINATE_DIMENSION = "XY"

    def __init__(self):
        """Initialize the transformation stage with query builders."""
        super().__init__(
            name="Transformation",
            description="Apply derivations and build geometries",
        )
        self.transformation_builder = TransformationBuilder()
        self.table_builder = TableBuilder()

    def execute(self, source: SourceConfig, context: Dict[str, Any]) -> None:
        """
        Apply transformations for a source.

        Args:
            source: Source configuration
            context: Shared context (must contain 'table_name')
        """
        table_name = context["table_name"]

        self._apply_derivations(source, table_name)
        self._build_geometries(source, table_name)

    def _apply_derivations(self, source: SourceConfig, table_name: str) -> None:
        """
        Compute derived columns using SQL expressions.

        Args:
            source: Source configuration
            table_name: Name of the table
        """
        if not source.attributes.derived:
            return

        with engine.connect() as connection:
            for attr in source.attributes.derived:
                # Build appropriate UPDATE statement
                if attr.type == DataType.GEOMETRY:
                    # Geometry derivations store as WKT text
                    column_name = f"{attr.name}_wkt"
                else:
                    column_name = attr.name

                update_sql = self.transformation_builder.build_derivation_update(
                    table_name, column_name, attr.expression
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

    def _build_geometries(self, source: SourceConfig, table_name: str) -> None:
        """
        Convert WKT text to SpatiaLite geometry objects.

        Args:
            source: Source configuration
            table_name: Name of the table
        """
        geometry_attr = self._find_geometry_attribute(source)

        if geometry_attr is None:
            return

        with engine.connect() as connection:
            try:
                # Add SpatiaLite geometry column
                add_geometry_sql = self.table_builder.build_add_geometry_column(
                    table_name,
                    geometry_attr.name,
                    geometry_attr.srid,
                    self.GEOMETRY_TYPE,
                    self.COORDINATE_DIMENSION,
                )
                connection.execute(sa.text(add_geometry_sql))

                # Populate geometry column from WKT
                update_sql = self.transformation_builder.build_geometry_update(
                    table_name, geometry_attr.name, geometry_attr.srid
                )

                # Execute with progress tracking
                with create_progress_bar(
                    1,
                    f"Building {table_name}.{geometry_attr.name}",
                    "column",
                ) as pbar:
                    connection.execute(sa.text(update_sql))
                    pbar.update(1)

                connection.commit()
            except sa.exc.DatabaseError as e:
                connection.rollback()
                raise RuntimeError(
                    f"Failed to build geometry column {geometry_attr.name} "
                    f"in table {table_name}: {e}"
                )

    def _find_geometry_attribute(self, source: SourceConfig) -> Optional[object]:
        """
        Find the geometry attribute in the source configuration.

        Checks both original and derived attributes.

        Args:
            source: Source configuration

        Returns:
            The geometry attribute object, or None if none exists
        """
        # Check original attributes
        for attr in source.attributes.original:
            if attr.type == DataType.GEOMETRY and not attr.drop:
                return attr

        # Check derived attributes
        for attr in source.attributes.derived:
            if attr.type == DataType.GEOMETRY:
                return attr

        return None
