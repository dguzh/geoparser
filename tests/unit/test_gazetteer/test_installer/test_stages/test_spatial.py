"""
Unit tests for geoparser/gazetteer/installer/stages/spatial.py

Tests the SpatialStage class.
"""

from unittest.mock import Mock, patch

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point

from geoparser.gazetteer.installer.model import (
    AttributesConfig,
    DataType,
    DerivedAttributeConfig,
    GeometryTransform,
    JoinOperandConfig,
    OriginalAttributeConfig,
    SelectConfig,
    SourceConfig,
    SourceKind,
    SpatialConditionConfig,
    ViewConfig,
    ViewJoinConfig,
)
from geoparser.gazetteer.installer.stages.spatial import SpatialStage


def _build_geometry_source(name: str, srid: int, derived: bool = False) -> SourceConfig:
    geometry_attr = (
        DerivedAttributeConfig(
            name="geometry",
            type=DataType.GEOMETRY,
            expression="'POINT(0 0)'",
            srid=srid,
        )
        if derived
        else OriginalAttributeConfig(
            name="geometry",
            type=DataType.GEOMETRY,
            srid=srid,
        )
    )
    attributes = AttributesConfig(
        original=[OriginalAttributeConfig(name="id", type=DataType.INTEGER)],
    )
    if derived:
        attributes.derived = [geometry_attr]
    else:
        attributes.original.append(geometry_attr)

    return SourceConfig(
        name=name,
        url=f"http://example.com/{name}.shp",
        file=f"{name}.shp",
        kind=SourceKind.SPATIAL,
        attributes=attributes,
    )


@pytest.mark.unit
class TestSpatialStageInit:
    """Test SpatialStage initialization."""

    def test_sets_name_and_description(self):
        """Test that stage name and description are set."""
        # Act
        stage = SpatialStage(source_map={})

        # Assert
        assert stage.name == "Spatial"
        assert stage.description == "Precompute spatial joins"

    def test_stores_source_map(self):
        """Test that the source map is stored for SRID resolution."""
        # Arrange
        source = _build_geometry_source("places", srid=4326)

        # Act
        stage = SpatialStage(source_map={"places": source})

        # Assert
        assert stage.source_map["places"] is source


@pytest.mark.unit
class TestSpatialStageExecute:
    """Test SpatialStage.execute() method."""

    def test_skips_when_source_has_no_view(self):
        """Test that spatial joins are skipped when the source has no view."""
        # Arrange
        source = _build_geometry_source("places", srid=4326)
        stage = SpatialStage(source_map={"places": source})

        # Act
        with patch.object(stage, "_precompute_join") as mock_precompute:
            stage.execute(source, {})

        # Assert
        mock_precompute.assert_not_called()

    def test_precomputes_spatial_join_conditions(self):
        """Test that only spatial join conditions are precomputed."""
        # Arrange
        source = _build_geometry_source("places", srid=4326)
        source.view = ViewConfig(
            select=[SelectConfig(column="places.id")],
            join=[
                ViewJoinConfig(
                    method="left join",
                    condition={
                        "type": "spatial",
                        "predicate": "within",
                        "left": {"column": "places.geometry"},
                        "right": {"column": "regions.geometry"},
                    },
                ),
                ViewJoinConfig(
                    method="left join",
                    condition={
                        "type": "attribute",
                        "predicate": "equals",
                        "left": {"column": "places.code"},
                        "right": {"column": "regions.code"},
                    },
                ),
            ],
        )
        stage = SpatialStage(source_map={"places": source})

        # Act
        with patch.object(stage, "_precompute_join") as mock_precompute:
            stage.execute(source, {})

        # Assert
        mock_precompute.assert_called_once()
        assert mock_precompute.call_args[0][0].is_spatial


@pytest.mark.unit
class TestSpatialStageGetSrid:
    """Test SpatialStage._get_srid() method."""

    def test_returns_srid_from_original_geometry(self):
        """Test that the SRID is resolved from an original geometry column."""
        # Arrange
        source = _build_geometry_source("places", srid=4326)
        stage = SpatialStage(source_map={"places": source})

        # Act
        srid = stage._get_srid("places", "geometry")

        # Assert
        assert srid == 4326

    def test_returns_srid_from_derived_geometry(self):
        """Test that the SRID is resolved from a derived geometry column."""
        # Arrange
        source = _build_geometry_source("places", srid=2056, derived=True)
        stage = SpatialStage(source_map={"places": source})

        # Act
        srid = stage._get_srid("places", "geometry")

        # Assert
        assert srid == 2056

    def test_raises_when_geometry_column_not_found(self):
        """Test that a missing geometry column raises ValueError."""
        # Arrange
        source = SourceConfig(
            name="places",
            url="http://example.com/places.csv",
            file="places.csv",
            kind=SourceKind.TABULAR,
            separator=",",
            attributes=AttributesConfig(
                original=[OriginalAttributeConfig(name="id", type=DataType.INTEGER)]
            ),
        )
        stage = SpatialStage(source_map={"places": source})

        # Act & Assert
        with pytest.raises(
            ValueError,
            match="Geometry column 'geometry' not found in source 'places'",
        ):
            stage._get_srid("places", "geometry")


@pytest.mark.unit
class TestSpatialStageLoadGeometries:
    """Test SpatialStage._load_geometries() method."""

    def test_applies_centroid_transform(self):
        """Test that a centroid transform is applied to loaded geometries."""
        # Arrange
        polygon_wkt = "POLYGON((0 0, 2 0, 2 2, 0 2, 0 0))"
        frame = pd.DataFrame({"rowid": [1], "geometry": [polygon_wkt]})
        stage = SpatialStage(source_map={})

        mock_connection = Mock()
        mock_connection.__enter__ = Mock(return_value=mock_connection)
        mock_connection.__exit__ = Mock(return_value=None)

        # Act
        with patch(
            "geoparser.gazetteer.installer.stages.spatial.get_connection",
            return_value=mock_connection,
        ), patch(
            "geoparser.gazetteer.installer.stages.spatial.pd.read_sql",
            return_value=frame,
        ):
            geometries = stage._load_geometries(
                "places",
                "geometry",
                4326,
                GeometryTransform.CENTROID,
            )

        # Assert
        assert geometries.geometry.iloc[0].equals(Point(1, 1))


@pytest.mark.unit
class TestSpatialStageComputeMapping:
    """Test SpatialStage._compute_mapping() method."""

    def test_returns_empty_series_when_geometries_are_empty(self):
        """Test that an empty mapping is returned when either side is empty."""
        # Arrange
        stage = SpatialStage(source_map={})
        left = gpd.GeoDataFrame(
            {"rowid": []},
            geometry=gpd.GeoSeries([], crs="EPSG:4326"),
            crs="EPSG:4326",
        )
        right = gpd.GeoDataFrame(
            {"rowid": [1]},
            geometry=gpd.GeoSeries([Point(0, 0)], crs="EPSG:4326"),
            crs="EPSG:4326",
        )

        # Act
        mapping = stage._compute_mapping(left, right, "within")

        # Assert
        assert mapping.empty
        assert mapping.dtype == "int64"


@pytest.mark.unit
class TestSpatialStagePrecomputeJoin:
    """Test SpatialStage._precompute_join() method."""

    def test_reprojects_right_geometries_when_srids_differ(self):
        """Test that the right geometries are reprojected to the left CRS."""
        # Arrange
        left_source = _build_geometry_source("places", srid=4326)
        right_source = _build_geometry_source("regions", srid=2056)
        stage = SpatialStage(
            source_map={"places": left_source, "regions": right_source}
        )
        condition = SpatialConditionConfig(
            predicate="within",
            left=JoinOperandConfig(column="places.geometry"),
            right=JoinOperandConfig(column="regions.geometry"),
        )

        left_geometries = gpd.GeoDataFrame(
            {"rowid": [1]},
            geometry=gpd.points_from_xy([8.0], [47.0], crs="EPSG:4326"),
        )
        right_geometries = gpd.GeoDataFrame(
            {"rowid": [10]},
            geometry=gpd.GeoSeries.from_wkt(
                [
                    "POLYGON(("
                    "2660000 1200000, "
                    "2670000 1200000, "
                    "2670000 1210000, "
                    "2660000 1210000, "
                    "2660000 1200000"
                    "))"
                ],
                crs="EPSG:2056",
            ),
        )
        # Act
        with patch.object(stage, "_get_srid", side_effect=[4326, 2056]), patch.object(
            stage,
            "_load_geometries",
            side_effect=[left_geometries, right_geometries],
        ), patch.object(
            stage,
            "_compute_mapping",
            wraps=stage._compute_mapping,
        ) as mock_compute, patch.object(
            stage,
            "_store_mapping",
        ):
            stage._precompute_join(condition)

        # Assert
        mock_compute.assert_called_once()
        right_passed = mock_compute.call_args[0][1]
        assert str(right_passed.crs) == str(left_geometries.crs)
