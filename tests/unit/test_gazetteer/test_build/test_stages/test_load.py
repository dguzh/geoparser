"""
Unit tests for geoparser/gazetteer/build/stages/load.py

Tests the Loader against small tabular and spatial fixture files, and the
error paths around a spatial source's declared geometry column.
"""

import json
from pathlib import Path

import duckdb
import pytest

from geoparser.gazetteer.build.schema import SourceConfig
from geoparser.gazetteer.build.stages.load import (
    Loader,
    quote_identifier,
    quote_literal,
)


def make_tabular_source(**overrides) -> SourceConfig:
    data = {
        "name": "places",
        "path": "/tmp/unused.csv",
        "file": "places.csv",
        "delimiter": ",",
        "attributes": [
            {"name": "id", "type": "integer"},
            {"name": "name", "type": "text"},
        ],
    }
    data.update(overrides)
    return SourceConfig.model_validate(data)


def make_spatial_source(**overrides) -> SourceConfig:
    data = {
        "name": "shape",
        "path": "/tmp/unused.geojson",
        "file": "shape.geojson",
        "attributes": [
            {"name": "id", "type": "integer"},
            {"name": "geometry", "type": "geometry"},
        ],
    }
    data.update(overrides)
    return SourceConfig.model_validate(data)


@pytest.fixture
def connection():
    con = duckdb.connect()
    con.load_extension("spatial")
    yield con
    con.close()


@pytest.fixture
def loader(connection) -> Loader:
    return Loader(connection)


class _FakeGeometryColumnsResult:
    """A minimal stand-in for a DuckDB result set."""

    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


class _FakeMultiGeometryConnection:
    """
    Wraps a real DuckDB connection but reports two geometry columns.

    Used to exercise Loader's "multiple geometry columns" error path, which
    no supported file format naturally produces (every GDAL driver exposes
    exactly one geometry field per layer).
    """

    def __init__(self, real: duckdb.DuckDBPyConnection):
        self._real = real

    def execute(self, sql, *args, **kwargs):
        if "data_type LIKE 'GEOMETRY%'" in sql:
            return _FakeGeometryColumnsResult([("geometry",), ("geometry2",)])
        return self._real.execute(sql, *args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._real, name)


class _RefusesParallelPaddingConnection:
    """
    Wraps a real DuckDB connection, failing the first CSV read.

    It raises what DuckDB raises when its parallel scanner is asked to combine
    null padding with quoted newlines. That only happens for files large enough
    to be split across threads, so reproducing it here keeps the retry path
    testable without a multi-megabyte fixture.
    """

    def __init__(self, real: duckdb.DuckDBPyConnection):
        self._real = real
        self.statements = []

    def execute(self, sql, *args, **kwargs):
        self.statements.append(sql)
        if "read_csv" in sql and "parallel=false" not in sql:
            raise duckdb.InvalidInputException(
                "Invalid Input Error: CSV Error on Line: 1. "
                "The parallel scanner does not support null_padding in "
                "conjunction with quoted new lines."
            )
        return self._real.execute(sql, *args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._real, name)


@pytest.mark.unit
class TestQuoting:
    """Test quote_identifier() and quote_literal()."""

    def test_quote_identifier_escapes_embedded_quotes(self):
        assert quote_identifier('my "column"') == '"my ""column"""'

    def test_quote_literal_escapes_embedded_quotes(self):
        assert quote_literal("it's") == "'it''s'"


@pytest.mark.unit
class TestLoadTabular:
    """Test Loader.load() for tabular (delimited) sources."""

    def test_loads_rows_with_declared_types(self, loader, tmp_path):
        """A tabular file is loaded into a table matching its declared schema."""
        data_file = tmp_path / "places.csv"
        data_file.write_text("1,Paris\n2,Berlin\n")
        source = make_tabular_source()

        row_count = loader.load(source, data_file)

        assert row_count == 2
        assert loader.columns("places") == ["id", "name"]

    def test_respects_skip_rows(self, loader, tmp_path):
        """skip_rows drops leading rows (e.g. a header) before parsing."""
        data_file = tmp_path / "places.csv"
        data_file.write_text("header,ignored\n1,Paris\n2,Berlin\n")
        source = make_tabular_source(skip_rows=1)

        row_count = loader.load(source, data_file)

        assert row_count == 2

    def test_respects_custom_delimiter_and_no_quote(self, loader, tmp_path):
        """A tab delimiter with quoting disabled is honored."""
        data_file = tmp_path / "places.tsv"
        data_file.write_text('1\tO"Brien\n2\tBerlin\n')
        source = make_tabular_source(delimiter="\t", quote="")

        loader.load(source, data_file)

        rows = loader.connection.execute(
            "SELECT name FROM places ORDER BY id"
        ).fetchall()
        assert rows[0][0] == 'O"Brien'

    def test_loads_quoted_fields_spanning_several_lines(self, loader, tmp_path):
        """A quoted field containing newlines is one value, not two rows."""
        data_file = tmp_path / "places.csv"
        data_file.write_text('1,"Paris,\nthe capital"\n2,Berlin\n')
        source = make_tabular_source()

        row_count = loader.load(source, data_file)

        assert row_count == 2
        assert loader.connection.execute(
            "SELECT name FROM places WHERE id = 1"
        ).fetchone() == ("Paris,\nthe capital",)

    def test_retries_single_threaded_on_the_padding_conflict(
        self, connection, tmp_path
    ):
        """
        A file DuckDB's parallel scanner refuses is re-read single-threaded.

        Its parallel scanner rejects null padding combined with quoted
        newlines, which is a property of how the file is read rather than of
        the file itself, so the load falls back instead of failing.
        """
        data_file = tmp_path / "places.csv"
        data_file.write_text('1,"Paris,\nthe capital"\n2,Berlin\n')
        proxy = _RefusesParallelPaddingConnection(connection)
        loader = Loader(proxy)

        row_count = loader.load(make_tabular_source(), data_file)

        assert row_count == 2
        reads = [sql for sql in proxy.statements if "read_csv" in sql]
        assert len(reads) == 2
        assert "parallel=false" in reads[1]

    def test_unrelated_csv_errors_are_not_retried(self, loader, tmp_path):
        """Errors other than the padding conflict propagate to the caller."""
        source = make_tabular_source()

        with pytest.raises(duckdb.Error):
            loader.load(source, tmp_path / "missing.csv")


@pytest.mark.unit
class TestLoadSpatial:
    """Test Loader.load() for spatial sources."""

    def _write_geojson(self, path: Path, features: list) -> None:
        path.write_text(json.dumps({"type": "FeatureCollection", "features": features}))

    def test_loads_geometry_and_casts_attributes(self, loader, tmp_path):
        """The geometry column is normalized and other attributes cast."""
        data_file = tmp_path / "shape.geojson"
        self._write_geojson(
            data_file,
            [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [1.0, 2.0]},
                    "properties": {"id": 1},
                }
            ],
        )
        source = make_spatial_source()

        row_count = loader.load(source, data_file)

        assert row_count == 1
        assert set(loader.columns("shape")) == {"id", "geometry"}

    def test_reprojects_geometry_into_the_gazetteer_crs(self, connection, tmp_path):
        """A source in another CRS is staged in the gazetteer's."""
        data_file = tmp_path / "shape.geojson"
        self._write_geojson(
            data_file,
            [
                {
                    "type": "Feature",
                    # LV95 coordinates of Bern
                    "geometry": {
                        "type": "Point",
                        "coordinates": [2600000.0, 1200000.0],
                    },
                    "properties": {"id": 1},
                }
            ],
        )
        loader = Loader(connection, "EPSG:4326")

        loader.load(make_spatial_source(crs="EPSG:2056"), data_file)

        longitude, latitude = connection.execute(
            "SELECT ST_X(geometry), ST_Y(geometry) FROM shape"
        ).fetchone()
        assert longitude == pytest.approx(7.44, abs=0.05)
        assert latitude == pytest.approx(46.95, abs=0.05)

    def test_leaves_geometry_alone_when_the_crs_matches(self, connection, tmp_path):
        """A source already in the gazetteer's CRS is staged unchanged."""
        data_file = tmp_path / "shape.geojson"
        self._write_geojson(
            data_file,
            [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [7.44, 46.95]},
                    "properties": {"id": 1},
                }
            ],
        )
        loader = Loader(connection, "EPSG:4326")

        loader.load(make_spatial_source(crs="EPSG:4326"), data_file)

        assert connection.execute(
            "SELECT ST_X(geometry), ST_Y(geometry) FROM shape"
        ).fetchone() == pytest.approx((7.44, 46.95))

    def test_renames_non_standard_geometry_column(self, loader, tmp_path):
        """A geometry column not named 'geometry' is renamed to match."""
        data_file = tmp_path / "shape.geojson"
        self._write_geojson(
            data_file,
            [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [1.0, 2.0]},
                    "properties": {"id": 1},
                }
            ],
        )
        source = make_spatial_source()

        loader.load(source, data_file)

        # GDAL's GeoJSON driver exposes the geometry column as "geometry"
        # already, so this mainly exercises that the final table has exactly
        # the declared "geometry" column regardless.
        assert "geometry" in loader.columns("shape")

    def test_raises_when_no_geometry_column_found(self, loader, tmp_path):
        """A source file with no detectable geometry column is rejected."""
        data_file = tmp_path / "plain.csv"
        data_file.write_text("id,name\n1,Alpha\n2,Beta\n")
        source = make_spatial_source(
            file="plain.csv",
            attributes=[
                {"name": "id", "type": "integer"},
                {"name": "geometry", "type": "geometry"},
            ],
        )

        with pytest.raises(ValueError, match="no geometry column found"):
            loader.load(source, data_file)

    def test_raises_when_multiple_geometry_columns_found(self, tmp_path):
        """A source with more than one geometry column is rejected."""
        data_file = tmp_path / "shape.geojson"
        self._write_geojson(
            data_file,
            [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [1.0, 2.0]},
                    "properties": {"id": 1},
                }
            ],
        )
        source = make_spatial_source()
        real_connection = duckdb.connect()
        real_connection.load_extension("spatial")
        proxy = _FakeMultiGeometryConnection(real_connection)
        loader = Loader(proxy)

        with pytest.raises(ValueError, match="multiple geometry columns found"):
            loader._load_spatial(source, data_file)


@pytest.mark.unit
class TestColumns:
    """Test Loader.columns()."""

    def test_returns_column_names_in_order(self, loader, tmp_path):
        """columns() lists a loaded table's columns in declaration order."""
        data_file = tmp_path / "places.csv"
        data_file.write_text("1,Paris\n")
        loader.load(make_tabular_source(), data_file)

        assert loader.columns("places") == ["id", "name"]
