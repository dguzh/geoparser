from typing import Any, Dict, Optional

import geopandas as gpd
import pandas as pd
import sqlalchemy as sa

from geoparser.db.db import get_connection
from geoparser.gazetteer.installer.model import (
    DataType,
    GeometryTransform,
    SourceConfig,
    SpatialConditionConfig,
)
from geoparser.gazetteer.installer.queries.spatial import spatial_join_column_name
from geoparser.gazetteer.installer.stages.base import Stage
from geoparser.gazetteer.installer.utils.progress import create_progress_bar

# Temporary table used to bulk-apply the precomputed spatial-join mapping.
_MAPPING_TABLE = "_geoparser_spatial_join_mapping"


class SpatialStage(Stage):
    """
    Precomputes spatial join conditions declared in a source's view.

    Spatial relationships (e.g. which administrative polygon contains each
    point) are computed in Python using GeoPandas' in-memory spatial index,
    replacing the need for a spatial database extension. For each spatial
    join, the matched right-table ``rowid`` is stored in a key column on the
    left table so the view can join on plain equality.
    """

    def __init__(self, source_map: Dict[str, SourceConfig]):
        """
        Initialize the spatial stage.

        Args:
            source_map: Mapping of source name to its configuration, used to
                resolve the spatial reference system of each geometry column
        """
        super().__init__(
            name="Spatial",
            description="Precompute spatial joins",
        )
        self.source_map = source_map

    def execute(self, source: SourceConfig, context: Dict[str, Any]) -> None:
        """
        Precompute all spatial join conditions for a source's view.

        Args:
            source: Source configuration
            context: Shared context (unused, kept for interface consistency)
        """
        if source.view is None or not source.view.join:
            return

        spatial_conditions = [
            join_item.condition
            for join_item in source.view.join
            if join_item.condition.is_spatial
        ]

        for condition in spatial_conditions:
            self._precompute_join(condition)

    def _precompute_join(self, condition: SpatialConditionConfig) -> None:
        """
        Precompute a single spatial join and store the result column.

        Args:
            condition: Spatial join condition
        """
        left_table = condition.left_source
        right_table = condition.right_source
        column = spatial_join_column_name(right_table)

        left_srid = self._get_srid(left_table, condition.left_column)
        right_srid = self._get_srid(right_table, condition.right_column)

        with create_progress_bar(
            1,
            f"Joining {left_table}.{condition.left_column}",
            "column",
        ) as pbar:
            left_geometries = self._load_geometries(
                left_table, condition.left_column, left_srid, condition.left.transform
            )
            right_geometries = self._load_geometries(
                right_table,
                condition.right_column,
                right_srid,
                condition.right.transform,
            )

            # Align coordinate reference systems before evaluating the predicate
            if left_srid != right_srid:
                right_geometries = right_geometries.to_crs(left_geometries.crs)

            mapping = self._compute_mapping(
                left_geometries, right_geometries, condition.predicate.value
            )
            self._store_mapping(left_table, column, mapping)

            pbar.update(1)

    def _get_srid(self, source_name: str, column_name: str) -> int:
        """
        Resolve the SRID of a geometry column from the source configuration.

        Args:
            source_name: Name of the source/table
            column_name: Name of the geometry column

        Returns:
            The SRID of the geometry column

        Raises:
            ValueError: If the geometry column cannot be found
        """
        source = self.source_map[source_name]

        for attr in source.attributes.original:
            if attr.name == column_name and attr.type == DataType.GEOMETRY:
                return attr.srid

        for attr in source.attributes.derived:
            if attr.name == column_name and attr.type == DataType.GEOMETRY:
                return attr.srid

        raise ValueError(
            f"Geometry column '{column_name}' not found in source '{source_name}'"
        )

    def _load_geometries(
        self,
        table_name: str,
        column_name: str,
        srid: int,
        transform: Optional[GeometryTransform],
    ) -> gpd.GeoDataFrame:
        """
        Load a table's geometries (as WKT) into a GeoDataFrame.

        Args:
            table_name: Name of the table to read
            column_name: Name of the geometry column (WKT text)
            srid: SRID of the geometry column
            transform: Optional geometry transform to apply (e.g. centroid)

        Returns:
            GeoDataFrame with a 'rowid' column and a geometry column
        """
        crs = f"EPSG:{srid}"

        with get_connection() as connection:
            frame = pd.read_sql(
                sa.text(
                    f"SELECT rowid AS rowid, {column_name} AS geometry "
                    f"FROM {table_name} WHERE {column_name} IS NOT NULL"
                ),
                connection,
            )

        geometry = gpd.GeoSeries.from_wkt(frame["geometry"], crs=crs)
        geometries = gpd.GeoDataFrame(frame[["rowid"]], geometry=geometry, crs=crs)

        if transform == GeometryTransform.CENTROID:
            geometries = geometries.set_geometry(geometries.geometry.centroid)

        return geometries

    def _compute_mapping(
        self,
        left_geometries: gpd.GeoDataFrame,
        right_geometries: gpd.GeoDataFrame,
        predicate: str,
    ) -> pd.Series:
        """
        Compute the left-rowid to right-rowid mapping via a spatial join.

        Args:
            left_geometries: Left geometries with a 'rowid' column
            right_geometries: Right geometries with a 'rowid' column
            predicate: Spatial predicate (e.g. "within")

        Returns:
            Series indexed by left rowid with the matched right rowid
        """
        if left_geometries.empty or right_geometries.empty:
            return pd.Series(dtype="int64")

        left = left_geometries.rename(columns={"rowid": "left_rowid"})
        right = right_geometries.rename(columns={"rowid": "right_rowid"})

        joined = gpd.sjoin(left, right, how="inner", predicate=predicate)

        # Keep the first match per left row (admin polygons do not overlap)
        joined = joined.drop_duplicates(subset="left_rowid", keep="first")

        return pd.Series(
            joined["right_rowid"].to_numpy(),
            index=joined["left_rowid"].to_numpy(),
        )

    def _store_mapping(
        self,
        table_name: str,
        column_name: str,
        mapping: pd.Series,
    ) -> None:
        """
        Add the key column to the left table and populate it from the mapping.

        Args:
            table_name: Name of the left table
            column_name: Name of the key column to create
            mapping: Series indexed by left rowid with the matched right rowid
        """
        with get_connection() as connection:
            connection.execute(
                sa.text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} INTEGER")
            )

            if not mapping.empty:
                mapping_frame = pd.DataFrame(
                    {
                        "left_rowid": mapping.index.to_numpy(),
                        "right_rowid": mapping.to_numpy(),
                    }
                )
                mapping_frame = mapping_frame.dropna(subset=["right_rowid"])
                mapping_frame["left_rowid"] = mapping_frame["left_rowid"].astype("int64")
                mapping_frame["right_rowid"] = mapping_frame["right_rowid"].astype(
                    "int64"
                )

                mapping_frame.to_sql(
                    _MAPPING_TABLE,
                    connection,
                    index=False,
                    if_exists="replace",
                )
                connection.execute(
                    sa.text(
                        f"CREATE INDEX IF NOT EXISTS {_MAPPING_TABLE}_left_rowid "
                        f"ON {_MAPPING_TABLE}(left_rowid)"
                    )
                )
                connection.execute(
                    sa.text(
                        f"UPDATE {table_name} SET {column_name} = "
                        f"(SELECT right_rowid FROM {_MAPPING_TABLE} "
                        f"WHERE {_MAPPING_TABLE}.left_rowid = {table_name}.rowid) "
                        f"WHERE rowid IN (SELECT left_rowid FROM {_MAPPING_TABLE})"
                    )
                )
                connection.execute(sa.text(f"DROP TABLE IF EXISTS {_MAPPING_TABLE}"))

            # Index the key column for efficient runtime joins
            connection.execute(
                sa.text(
                    f"CREATE INDEX IF NOT EXISTS idx_{table_name}_{column_name} "
                    f"ON {table_name}({column_name})"
                )
            )

            connection.commit()
