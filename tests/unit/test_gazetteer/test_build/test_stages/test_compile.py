"""
Unit tests for geoparser/gazetteer/build/stages/compile.py

Tests the projection compiler by executing the generated SQL against small
in-memory DuckDB datasets and asserting on the produced rows.
"""

import json
import typing as t

import duckdb
import pytest

from geoparser.gazetteer.build.schema import GazetteerConfig
from geoparser.gazetteer.build.stages.compile import (
    CompileError,
    ProjectionCompiler,
    qualifiers,
    qualify_expression,
)


def build_compiler(config_data: dict) -> t.Tuple[GazetteerConfig, ProjectionCompiler]:
    """Validate a config and build a compiler with a catalog from its sources."""
    config = GazetteerConfig.model_validate(config_data)
    catalog = {
        source.name: [a.name for a in source.attributes] for source in config.sources
    }
    return config, ProjectionCompiler(config, catalog)


def tabular(name: str, *columns: t.Tuple[str, str]) -> dict:
    """A tabular source declaration with (column, type) pairs."""
    return {
        "name": name,
        "path": f"{name}.csv",
        "file": f"{name}.csv",
        "delimiter": ",",
        "attributes": [{"name": column, "type": type_} for column, type_ in columns],
    }


def spatial(name: str, *columns: t.Tuple[str, str]) -> dict:
    """A spatial source declaration; must include a ('geometry', 'geometry') pair."""
    return {
        "name": name,
        "path": f"{name}.shp",
        "file": f"{name}.shp",
        "attributes": [{"name": column, "type": type_} for column, type_ in columns],
    }


def run_features(
    connection: duckdb.DuckDBPyConnection,
    compiler: ProjectionCompiler,
    config: GazetteerConfig,
) -> t.Dict[str, dict]:
    """
    Run all feature queries and index the rows by identifier.

    Mirrors the builder: the feature query keeps the first row's geometry, and
    geometries of duplicated identifiers are unioned via the separate
    duplicate-geometry query.
    """
    results = {}
    for feature in config.features:
        merged_geometry = {}
        duplicate_query = compiler.duplicate_geometry_query(feature)
        if duplicate_query is not None:
            for identifier, geometry in connection.execute(duplicate_query).fetchall():
                merged_geometry[identifier] = geometry
        for identifier, source, data, geometry in connection.execute(
            compiler.feature_query(feature)
        ).fetchall():
            results[identifier] = {
                "source": source,
                "data": json.loads(data),
                "geometry": merged_geometry.get(identifier, geometry),
            }
    return results


def run_names(
    connection: duckdb.DuckDBPyConnection,
    compiler: ProjectionCompiler,
    config: GazetteerConfig,
) -> t.Dict[str, t.Set[str]]:
    """Run all name queries and collect names per identifier."""
    names: t.Dict[str, t.Set[str]] = {}
    for feature in config.features:
        for query in compiler.name_queries(feature):
            for identifier, text in connection.execute(query).fetchall():
                names.setdefault(identifier, set()).add(text)
    return names


@pytest.fixture
def connection():
    con = duckdb.connect()
    con.load_extension("spatial")
    yield con
    con.close()


@pytest.mark.unit
class TestBasicProjection:
    """Test projection of a single source into features and names."""

    def make_places(self, connection):
        connection.execute(
            "CREATE TABLE places (id INTEGER, name VARCHAR, population INTEGER)"
        )
        connection.execute(
            "INSERT INTO places VALUES (1, 'Paris', 2100000), (2, 'Berlin', 3600000)"
        )

    def config_data(self, **feature_overrides) -> dict:
        feature = {
            "source": "places",
            "identifier": "id",
            "names": ["name"],
            "data": ["name", "population"],
        }
        feature.update(feature_overrides)
        return {
            "name": "testgaz",
            "sources": [
                tabular(
                    "places",
                    ("id", "integer"),
                    ("name", "text"),
                    ("population", "integer"),
                )
            ],
            "features": [feature],
        }

    def test_projects_features_with_json_data(self, connection):
        """Each row becomes a feature with its data as JSON."""
        self.make_places(connection)
        config, compiler = build_compiler(self.config_data())

        features = run_features(connection, compiler, config)

        assert features["1"]["source"] == "places"
        assert features["1"]["data"] == {"name": "Paris", "population": 2100000}
        assert features["2"]["data"] == {"name": "Berlin", "population": 3600000}

    def test_projects_names(self, connection):
        """Name columns produce (identifier, text) rows."""
        self.make_places(connection)
        config, compiler = build_compiler(self.config_data())

        names = run_names(connection, compiler, config)

        assert names == {"1": {"Paris"}, "2": {"Berlin"}}

    def test_name_expression(self, connection):
        """Names can be scalar SQL expressions."""
        self.make_places(connection)
        config, compiler = build_compiler(self.config_data(names=["upper(name)"]))

        names = run_names(connection, compiler, config)

        assert names == {"1": {"PARIS"}, "2": {"BERLIN"}}

    def test_data_expression(self, connection):
        """Data values can be scalar SQL expressions with an alias."""
        self.make_places(connection)
        config, compiler = build_compiler(
            self.config_data(data=["upper(name) AS shout"])
        )

        features = run_features(connection, compiler, config)

        assert features["1"]["data"] == {"shout": "PARIS"}

    def test_rows_with_null_identifier_are_dropped(self, connection):
        """Rows without an identifier value produce no feature."""
        self.make_places(connection)
        connection.execute("INSERT INTO places VALUES (NULL, 'Ghost', 0)")
        config, compiler = build_compiler(self.config_data())

        features = run_features(connection, compiler, config)

        assert set(features) == {"1", "2"}

    def test_empty_and_null_names_are_dropped(self, connection):
        """NULL or blank name values produce no name rows."""
        self.make_places(connection)
        connection.execute("INSERT INTO places VALUES (3, NULL, 0), (4, '  ', 0)")
        config, compiler = build_compiler(self.config_data())

        names = run_names(connection, compiler, config)

        assert set(names) == {"1", "2"}

    def test_unknown_data_column_raises_with_hint(self, connection):
        """Unknown data columns fail compilation with the available columns."""
        self.make_places(connection)
        config, compiler = build_compiler(self.config_data(data=["nonexistent"]))

        with pytest.raises(CompileError, match="Available columns"):
            compiler.feature_query(config.features[0])

    def test_unknown_name_column_raises(self, connection):
        """Unknown name columns fail compilation."""
        self.make_places(connection)
        config, compiler = build_compiler(self.config_data(names=["nonexistent"]))

        with pytest.raises(CompileError, match="unknown column 'nonexistent'"):
            compiler.name_queries(config.features[0])


@pytest.mark.unit
class TestOwnSourceReferences:
    """Test that identifier and geometry may only read the block's own source."""

    def config_data(self, **feature_overrides) -> dict:
        feature = {
            "source": "places",
            "joins": ["LEFT JOIN regions r ON region_code = r.code"],
            "identifier": "id",
            "names": ["name"],
        }
        feature.update(feature_overrides)
        return {
            "name": "testgaz",
            "sources": [
                tabular(
                    "places",
                    ("id", "integer"),
                    ("name", "text"),
                    ("region_code", "text"),
                    ("lon", "real"),
                    ("lat", "real"),
                ),
                spatial("regions", ("code", "text"), ("geometry", "geometry")),
            ],
            "features": [feature],
        }

    def test_geometry_from_joined_source_is_rejected(self):
        """A geometry read from a joined source names the offending source."""
        config, compiler = build_compiler(self.config_data(geometry="r.geometry"))

        with pytest.raises(CompileError, match="geometry reads from 'r'"):
            compiler.feature_query(config.features[0])

    def test_identifier_from_joined_source_is_rejected(self):
        """An identifier read from a joined source is rejected too."""
        config, compiler = build_compiler(self.config_data(identifier="r.code"))

        with pytest.raises(CompileError, match="identifier reads from 'r'"):
            compiler.feature_query(config.features[0])

    def test_expression_over_own_columns_is_accepted(self):
        """Expressions over the block's own columns compile as before."""
        config, compiler = build_compiler(
            self.config_data(identifier="'place:' || id", geometry="ST_Point(lon, lat)")
        )

        query = compiler.feature_query(config.features[0])

        assert 'src."id"' in query
        assert 'src."lon"' in query

    def test_joined_source_in_data_is_accepted(self):
        """The restriction applies to identifier and geometry only."""
        config, compiler = build_compiler(self.config_data(data=["r.code AS region"]))

        assert "r.code" in compiler.feature_query(config.features[0])


@pytest.mark.unit
class TestSplitNames:
    """Test splitting multi-value name fields via a SQL expression."""

    def test_split_produces_one_name_per_value(self, connection):
        """An expression that unnests a split field yields individual names."""
        connection.execute("CREATE TABLE places (id INTEGER, alternates VARCHAR)")
        connection.execute(
            "INSERT INTO places VALUES (1, 'Wien, Vienna , Vindobona'), (2, '')"
        )
        config, compiler = build_compiler(
            {
                "name": "testgaz",
                "sources": [
                    tabular("places", ("id", "integer"), ("alternates", "text"))
                ],
                "features": [
                    {
                        "source": "places",
                        "identifier": "id",
                        "names": ["unnest(string_split(alternates, ','))"],
                    }
                ],
            }
        )

        names = run_names(connection, compiler, config)

        assert names == {"1": {"Wien", "Vienna", "Vindobona"}}


@pytest.mark.unit
class TestDuplicateMerge:
    """Test merging of rows that share an identifier."""

    def make_duplicates(self, connection):
        connection.execute(
            "CREATE TABLE places (id INTEGER, name VARCHAR, height INTEGER)"
        )
        connection.execute(
            "INSERT INTO places VALUES "
            "(1, 'North Peak', 800), (1, 'South Peak', 1200), (2, 'Valley', 300)"
        )

    def config_data(self, data=None) -> dict:
        feature = {
            "source": "places",
            "identifier": "id",
            "names": ["name"],
            "data": data or ["name", "height"],
        }
        return {
            "name": "testgaz",
            "sources": [
                tabular(
                    "places", ("id", "integer"), ("name", "text"), ("height", "integer")
                )
            ],
            "features": [feature],
        }

    def test_duplicate_rows_merge_into_one_feature(self, connection):
        """Rows sharing an identifier become a single feature."""
        self.make_duplicates(connection)
        config, compiler = build_compiler(self.config_data())

        features = run_features(connection, compiler, config)

        assert set(features) == {"1", "2"}

    def test_names_are_collected_across_duplicates(self, connection):
        """All names of duplicate rows are kept."""
        self.make_duplicates(connection)
        config, compiler = build_compiler(self.config_data())

        names = run_names(connection, compiler, config)

        assert names["1"] == {"North Peak", "South Peak"}

    def test_data_comes_from_first_row(self, connection):
        """Data values are taken from the first row of the group."""
        self.make_duplicates(connection)
        config, compiler = build_compiler(self.config_data())

        features = run_features(connection, compiler, config)

        assert features["1"]["data"]["name"] == "North Peak"
        assert features["1"]["data"]["height"] == 800


@pytest.mark.unit
class TestGeometry:
    """Test geometry projection and merging."""

    def test_point_geometry_from_coordinates(self, connection):
        """A point expression over lon/lat columns becomes a WKB point."""
        connection.execute(
            "CREATE TABLE places (id INTEGER, name VARCHAR, lon DOUBLE, lat DOUBLE)"
        )
        connection.execute(
            "INSERT INTO places VALUES (1, 'A', 1.5, 42.5), (2, 'B', NULL, NULL)"
        )
        config, compiler = build_compiler(
            {
                "name": "testgaz",
                "sources": [
                    tabular(
                        "places",
                        ("id", "integer"),
                        ("name", "text"),
                        ("lon", "real"),
                        ("lat", "real"),
                    )
                ],
                "features": [
                    {
                        "source": "places",
                        "identifier": "id",
                        "names": ["name"],
                        "geometry": "ST_Point(lon, lat)",
                    }
                ],
            }
        )

        features = run_features(connection, compiler, config)

        from shapely import wkb

        point = wkb.loads(bytes(features["1"]["geometry"]))
        assert (point.x, point.y) == (1.5, 42.5)
        # ST_Point over NULL coordinates yields no geometry
        assert features["2"]["geometry"] is None

    def test_geometry_union_merge(self, connection):
        """Geometries of duplicate rows are combined by union."""
        connection.execute(
            "CREATE TABLE places (id INTEGER, name VARCHAR, geometry GEOMETRY)"
        )
        connection.execute(
            "INSERT INTO places VALUES "
            "(1, 'Multi', ST_Point(0, 0)), (1, 'Multi', ST_Point(1, 1))"
        )
        config, compiler = build_compiler(
            {
                "name": "testgaz",
                "sources": [
                    spatial(
                        "places",
                        ("id", "integer"),
                        ("name", "text"),
                        ("geometry", "geometry"),
                    )
                ],
                "features": [
                    {
                        "source": "places",
                        "identifier": "id",
                        "names": ["name"],
                        "geometry": "geometry",
                    }
                ],
            }
        )

        features = run_features(connection, compiler, config)

        from shapely import wkb

        union = wkb.loads(bytes(features["1"]["geometry"]))
        assert union.geom_type == "MultiPoint"
        assert len(union.geoms) == 2

    def test_staged_geometry_column_is_not_transformed_again(self, connection):
        """
        A geometry column is passed through whatever CRS its source declares.

        Spatial sources are re-projected as they are staged (see the loader),
        so transforming here as well would move the geometry twice.
        """
        connection.execute(
            "CREATE TABLE places (id INTEGER, name VARCHAR, geometry GEOMETRY)"
        )
        connection.execute(
            "INSERT INTO places VALUES (1, 'Bern', ST_Point(7.44, 46.95))"
        )
        config, compiler = build_compiler(
            {
                "name": "testgaz",
                "crs": "EPSG:4326",
                "sources": [
                    spatial(
                        "places",
                        ("id", "integer"),
                        ("name", "text"),
                        ("geometry", "geometry"),
                    )
                    | {"crs": "EPSG:2056"}
                ],
                "features": [
                    {
                        "source": "places",
                        "identifier": "id",
                        "names": ["name"],
                        "geometry": "geometry",
                    }
                ],
            }
        )

        features = run_features(connection, compiler, config)

        from shapely import wkb

        point = wkb.loads(bytes(features["1"]["geometry"]))
        assert (point.x, point.y) == pytest.approx((7.44, 46.95))

    def test_constructed_geometry_is_reprojected_to_gazetteer_crs(self, connection):
        """A geometry built from coordinate columns is transformed here."""
        connection.execute(
            "CREATE TABLE places (id INTEGER, name VARCHAR, e DOUBLE, n DOUBLE)"
        )
        # LV95 coordinates of Bern
        connection.execute("INSERT INTO places VALUES (1, 'Bern', 2600000, 1200000)")
        config, compiler = build_compiler(
            {
                "name": "testgaz",
                "crs": "EPSG:4326",
                "sources": [
                    tabular(
                        "places",
                        ("id", "integer"),
                        ("name", "text"),
                        ("e", "real"),
                        ("n", "real"),
                    )
                    | {"crs": "EPSG:2056"}
                ],
                "features": [
                    {
                        "source": "places",
                        "identifier": "id",
                        "names": ["name"],
                        "geometry": "ST_Point(e, n)",
                    }
                ],
            }
        )

        features = run_features(connection, compiler, config)

        from shapely import wkb

        point = wkb.loads(bytes(features["1"]["geometry"]))
        assert point.x == pytest.approx(7.44, abs=0.05)
        assert point.y == pytest.approx(46.95, abs=0.05)


@pytest.mark.unit
class TestJoins:
    """Test raw SQL joins that enrich a feature block."""

    def make_data(self, connection):
        connection.execute(
            "CREATE TABLE places "
            "(id INTEGER, name VARCHAR, country_code VARCHAR, admin_code VARCHAR)"
        )
        connection.execute(
            "INSERT INTO places VALUES "
            "(1, 'Bern', 'CH', 'BE'), (2, 'Nowhere', 'XX', 'YY')"
        )
        connection.execute("CREATE TABLE countries (code VARCHAR, label VARCHAR)")
        connection.execute("INSERT INTO countries VALUES ('CH', 'Switzerland')")
        connection.execute("CREATE TABLE admins (code VARCHAR, label VARCHAR)")
        connection.execute("INSERT INTO admins VALUES ('CH.BE', 'Canton of Bern')")

    def places_source(self) -> dict:
        return tabular(
            "places",
            ("id", "integer"),
            ("name", "text"),
            ("country_code", "text"),
            ("admin_code", "text"),
        )

    def test_joined_column_becomes_data(self, connection):
        """A qualified reference to a joined table becomes a data value."""
        self.make_data(connection)
        config, compiler = build_compiler(
            {
                "name": "testgaz",
                "sources": [
                    self.places_source(),
                    tabular("countries", ("code", "text"), ("label", "text")),
                ],
                "features": [
                    {
                        "source": "places",
                        "joins": [
                            "LEFT JOIN countries ON country_code = countries.code"
                        ],
                        "identifier": "id",
                        "names": ["name"],
                        "data": [
                            "name",
                            "countries.label AS country_name",
                        ],
                    }
                ],
            }
        )

        features = run_features(connection, compiler, config)

        assert features["1"]["data"]["country_name"] == "Switzerland"
        assert features["2"]["data"]["country_name"] is None

    def test_join_using_clause_has_no_on_condition_to_qualify(self, connection):
        """A join without an ON condition (e.g. USING) is passed through as-is."""
        connection.execute(
            "CREATE TABLE places (id INTEGER, name VARCHAR, code VARCHAR)"
        )
        connection.execute("INSERT INTO places VALUES (1, 'Bern', 'CH')")
        connection.execute("CREATE TABLE countries (code VARCHAR, label VARCHAR)")
        connection.execute("INSERT INTO countries VALUES ('CH', 'Switzerland')")
        config, compiler = build_compiler(
            {
                "name": "testgaz",
                "sources": [
                    tabular(
                        "places", ("id", "integer"), ("name", "text"), ("code", "text")
                    ),
                    tabular("countries", ("code", "text"), ("label", "text")),
                ],
                "features": [
                    {
                        "source": "places",
                        "joins": ["JOIN countries USING (code)"],
                        "identifier": "id",
                        "names": ["name"],
                        "data": ["name", "countries.label AS country_name"],
                    }
                ],
            }
        )

        features = run_features(connection, compiler, config)

        assert features["1"]["data"]["country_name"] == "Switzerland"

    def test_join_on_expression(self, connection):
        """The join condition can be an arbitrary SQL expression."""
        self.make_data(connection)
        config, compiler = build_compiler(
            {
                "name": "testgaz",
                "sources": [
                    self.places_source(),
                    tabular("admins", ("code", "text"), ("label", "text")),
                ],
                "features": [
                    {
                        "source": "places",
                        "joins": [
                            "LEFT JOIN admins "
                            "ON country_code || '.' || admin_code = admins.code"
                        ],
                        "identifier": "id",
                        "names": ["name"],
                        "data": [
                            "name",
                            "admins.label AS admin_name",
                        ],
                    }
                ],
            }
        )

        features = run_features(connection, compiler, config)

        assert features["1"]["data"]["admin_name"] == "Canton of Bern"

    def test_join_chains_off_earlier_join(self, connection):
        """A later join can reference a table joined earlier."""
        connection.execute("CREATE TABLE places (id INTEGER, name VARCHAR, a VARCHAR)")
        connection.execute("INSERT INTO places VALUES (1, 'X', 'a1')")
        connection.execute("CREATE TABLE level1 (code VARCHAR, parent VARCHAR)")
        connection.execute("INSERT INTO level1 VALUES ('a1', 'b1')")
        connection.execute("CREATE TABLE level2 (code VARCHAR, label VARCHAR)")
        connection.execute("INSERT INTO level2 VALUES ('b1', 'Top level')")
        config, compiler = build_compiler(
            {
                "name": "testgaz",
                "sources": [
                    tabular(
                        "places", ("id", "integer"), ("name", "text"), ("a", "text")
                    ),
                    tabular("level1", ("code", "text"), ("parent", "text")),
                    tabular("level2", ("code", "text"), ("label", "text")),
                ],
                "features": [
                    {
                        "source": "places",
                        "joins": [
                            "LEFT JOIN level1 ON a = level1.code",
                            "LEFT JOIN level2 ON level1.parent = level2.code",
                        ],
                        "identifier": "id",
                        "names": ["name"],
                        "data": ["level2.label AS parent_label"],
                    }
                ],
            }
        )

        features = run_features(connection, compiler, config)

        assert features["1"]["data"]["parent_label"] == "Top level"

    def test_spatial_join(self, connection):
        """A spatial join clause matches the feature geometry against boundaries."""
        connection.execute(
            "CREATE TABLE places (id INTEGER, name VARCHAR, lon DOUBLE, lat DOUBLE)"
        )
        connection.execute(
            "INSERT INTO places VALUES (1, 'Inside', 0.5, 0.5), (2, 'Outside', 5, 5)"
        )
        connection.execute("CREATE TABLE zones (zone_name VARCHAR, geometry GEOMETRY)")
        connection.execute(
            "INSERT INTO zones VALUES "
            "('Unit Square', ST_GeomFromText('POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))'))"
        )
        config, compiler = build_compiler(
            {
                "name": "testgaz",
                "sources": [
                    tabular(
                        "places",
                        ("id", "integer"),
                        ("name", "text"),
                        ("lon", "real"),
                        ("lat", "real"),
                    ),
                    spatial("zones", ("zone_name", "text"), ("geometry", "geometry")),
                ],
                "features": [
                    {
                        "source": "places",
                        "joins": [
                            "LEFT JOIN zones "
                            "ON ST_Within(ST_Point(lon, lat), zones.geometry)"
                        ],
                        "identifier": "id",
                        "geometry": "ST_Point(lon, lat)",
                        "names": ["name"],
                        "data": ["zones.zone_name"],
                    }
                ],
            }
        )

        features = run_features(connection, compiler, config)

        assert features["1"]["data"]["zone_name"] == "Unit Square"
        assert features["2"]["data"]["zone_name"] is None

    def test_spatial_join_qualifies_ambiguous_geometry(self, connection):
        """A bare geometry column in an ON condition is qualified to the source.

        Both the source and the joined source expose a ``geometry`` column, so
        an unqualified reference would be ambiguous; the compiler qualifies it
        to ``src`` implicitly.
        """
        connection.execute("CREATE TABLE places (id INTEGER, geometry GEOMETRY)")
        connection.execute("INSERT INTO places VALUES (1, ST_Point(0.5, 0.5))")
        connection.execute("CREATE TABLE zones (zone_name VARCHAR, geometry GEOMETRY)")
        connection.execute(
            "INSERT INTO zones VALUES "
            "('Unit Square', ST_GeomFromText('POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))'))"
        )
        config, compiler = build_compiler(
            {
                "name": "testgaz",
                "sources": [
                    spatial("places", ("id", "integer"), ("geometry", "geometry")),
                    spatial("zones", ("zone_name", "text"), ("geometry", "geometry")),
                ],
                "features": [
                    {
                        "source": "places",
                        "joins": [
                            "LEFT JOIN zones "
                            "ON ST_Within(ST_Centroid(geometry), zones.geometry)"
                        ],
                        "identifier": "id",
                        "geometry": "geometry",
                        "names": ["CAST(id AS VARCHAR)"],
                        "data": ["zones.zone_name"],
                    }
                ],
            }
        )

        features = run_features(connection, compiler, config)

        assert features["1"]["data"]["zone_name"] == "Unit Square"

    def test_bare_and_qualified_references_pick_different_columns(self, connection):
        """A bare name is the source column; a qualified name is the joined one."""
        connection.execute(
            "CREATE TABLE places (id INTEGER, name VARCHAR, label VARCHAR)"
        )
        connection.execute("INSERT INTO places VALUES (1, 'X', 'base label')")
        connection.execute("CREATE TABLE extra (place_id INTEGER, label VARCHAR)")
        connection.execute("INSERT INTO extra VALUES (1, 'joined label')")
        config, compiler = build_compiler(
            {
                "name": "testgaz",
                "sources": [
                    tabular(
                        "places", ("id", "integer"), ("name", "text"), ("label", "text")
                    ),
                    tabular("extra", ("place_id", "integer"), ("label", "text")),
                ],
                "features": [
                    {
                        "source": "places",
                        "joins": ["LEFT JOIN extra ON id = extra.place_id"],
                        "identifier": "id",
                        "names": ["name"],
                        "data": [
                            "label",
                            "extra.label AS joined_label",
                        ],
                    }
                ],
            }
        )

        features = run_features(connection, compiler, config)

        assert features["1"]["data"]["label"] == "base label"
        assert features["1"]["data"]["joined_label"] == "joined label"


@pytest.mark.unit
class TestQualifyExpression:
    """Test qualification of bare column references in expressions."""

    def test_qualifies_bare_columns(self):
        result = qualify_expression(
            "code || name", {"code": 'src."code"', "name": 'src."name"'}
        )

        assert result == 'src."code" || src."name"'

    def test_leaves_string_literals_alone(self):
        result = qualify_expression("code || '.code'", {"code": 'src."code"'})

        assert result == "src.\"code\" || '.code'"

    def test_leaves_function_names_alone(self):
        result = qualify_expression("upper(upper)", {"upper": 'src."upper"'})

        assert result == 'upper(src."upper")'

    def test_leaves_qualified_references_alone(self):
        result = qualify_expression("other.code", {"code": 'src."code"'})

        assert result == "other.code"

    def test_leaves_unknown_identifiers_alone(self):
        result = qualify_expression("something_else", {"code": 'src."code"'})

        assert result == "something_else"


@pytest.mark.unit
class TestQualifiers:
    """Test detection of the tables an expression reads columns from."""

    def test_finds_qualified_references(self):
        assert qualifiers("a.code || b.name") == {"a", "b"}

    def test_ignores_bare_and_final_components(self):
        assert qualifiers("code || upper(name)") == set()

    def test_ignores_string_literals(self):
        assert qualifiers("code || 'a.b'") == set()

    def test_ignores_decimal_numbers(self):
        assert qualifiers("ST_Point(lon + 0.5, lat)") == set()

    def test_unquotes_quoted_qualifiers(self):
        assert qualifiers('"my source"."my column"') == {"my source"}
