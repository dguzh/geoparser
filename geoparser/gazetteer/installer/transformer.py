import sqlalchemy as sa
from tqdm.auto import tqdm

from geoparser.db.engine import engine
from geoparser.gazetteer.model import DataType, SourceConfig


class DataTransformer:
    """Transforms data by applying derivations and building geometries."""

    def apply_derivations(self, source_config: SourceConfig, table_name: str) -> None:
        """
        Create derived columns in a table using SQL expressions.

        Args:
            source_config: Source configuration
            table_name: Name of the table to create derivations for
        """
        if not source_config.derivations:
            return

        with engine.connect() as connection:
            for derivation in source_config.derivations:
                # Handle geometry derivations - store as WKT text
                if derivation.type == DataType.GEOMETRY:
                    update_sql = (
                        f"UPDATE {table_name} "
                        f"SET {derivation.name}_wkt = {derivation.expression}"
                    )
                else:
                    # Regular derivation
                    update_sql = (
                        f"UPDATE {table_name} "
                        f"SET {derivation.name} = {derivation.expression}"
                    )

                # Execute with progress bar
                with tqdm(
                    total=1,
                    desc=f"Deriving {table_name}.{derivation.name}",
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
            # Add SpatiaLite geometry column
            add_geometry_sql = (
                f"SELECT AddGeometryColumn('{table_name}', '{geometry_item.name}', "
                f"{geometry_item.srid}, 'GEOMETRY', 'XY')"
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

            connection.commit()

    def _find_geometry_item(self, source_config: SourceConfig):
        """
        Find the geometry attribute or derivation (if any) in the source config.

        Returns:
            The geometry attribute/derivation object, or None if none exists
        """
        # Check attributes first
        for attr in source_config.attributes:
            if attr.type == DataType.GEOMETRY and not attr.drop:
                return attr

        # Check derivations
        for deriv in source_config.derivations:
            if deriv.type == DataType.GEOMETRY:
                return deriv

        return None
