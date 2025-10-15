import sqlalchemy as sa
from tqdm.auto import tqdm

from geoparser.db.engine import engine
from geoparser.gazetteer.model import DataType, SourceConfig


class DataTransformer:
    """Transforms data by applying derivations and building geometries."""

    # SpatiaLite geometry type for AddGeometryColumn
    GEOMETRY_TYPE = "GEOMETRY"
    # Coordinate dimension for spatial columns (2D: XY)
    COORDINATE_DIMENSION = "XY"

    def apply_derivations(self, source_config: SourceConfig, table_name: str) -> None:
        """
        Create derived columns in a table using SQL expressions.

        Args:
            source_config: Source configuration
            table_name: Name of the table to create derivations for
        """
        if not source_config.attributes.derived:
            return

        with engine.connect() as connection:
            for attr in source_config.attributes.derived:
                # Handle geometry derivations - store as WKT text
                if attr.type == DataType.GEOMETRY:
                    update_sql = (
                        f"UPDATE {table_name} "
                        f"SET {attr.name}_wkt = {attr.expression}"
                    )
                else:
                    # Regular derivation
                    update_sql = (
                        f"UPDATE {table_name} " f"SET {attr.name} = {attr.expression}"
                    )

                # Execute with progress bar
                with tqdm(
                    total=1,
                    desc=f"Deriving {table_name}.{attr.name}",
                    unit="column",
                ) as pbar:
                    connection.execute(sa.text(update_sql))
                    pbar.update(1)

            connection.commit()

    def build_geometry(self, source_config: SourceConfig, table_name: str) -> None:
        """
        Convert WKT text in geometry columns to proper SpatiaLite geometries.

        Args:
            source_config: Source configuration
            table_name: Name of the table to update
        """
        geometry_item = self._find_geometry_item(source_config)

        if geometry_item is None:
            return

        with engine.connect() as connection:
            try:
                # Add SpatiaLite geometry column
                add_geometry_sql = (
                    f"SELECT AddGeometryColumn('{table_name}', '{geometry_item.name}', "
                    f"{geometry_item.srid}, '{self.GEOMETRY_TYPE}', '{self.COORDINATE_DIMENSION}')"
                )
                connection.execute(sa.text(add_geometry_sql))

                # Populate geometry column from WKT text
                update_sql = (
                    f"UPDATE {table_name} "
                    f"SET {geometry_item.name} = GeomFromText({geometry_item.name}_wkt, {geometry_item.srid}) "
                    f"WHERE {geometry_item.name}_wkt IS NOT NULL"
                )

                # Execute with progress bar
                with tqdm(
                    total=1,
                    desc=f"Building {table_name}.{geometry_item.name}",
                    unit="column",
                ) as pbar:
                    connection.execute(sa.text(update_sql))
                    pbar.update(1)

                # Commit the transaction
                connection.commit()
            except sa.exc.DatabaseError as e:
                # Roll back on error to maintain database consistency
                connection.rollback()
                raise RuntimeError(
                    f"Failed to build geometry column {geometry_item.name} in table {table_name}: {e}"
                )

    def _find_geometry_item(self, source_config: SourceConfig):
        """
        Find the geometry attribute (original or derived) in the source config.

        Returns:
            The geometry attribute object, or None if none exists
        """
        # Check original attributes first
        for attr in source_config.attributes.original:
            if attr.type == DataType.GEOMETRY and not attr.drop:
                return attr

        # Check derived attributes
        for attr in source_config.attributes.derived:
            if attr.type == DataType.GEOMETRY:
                return attr

        return None
