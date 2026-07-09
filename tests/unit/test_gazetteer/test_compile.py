"""
Unit tests for geoparser/gazetteer/build/compile.py

Tests the projection compiler by executing the generated SQL against small
in-memory DuckDB datasets and asserting on the produced rows.
"""

import json
import typing as t

import duckdb
import pytest

from geoparser.gazetteer.build.compile import (
    CompileError,
    ProjectionCompiler,
    qualify_expression,
)
from geoparser.gazetteer.config import GazetteerConfig


def build_compiler(
    connection: duckdb.DuckDBPyConnection, config_data: dict
) -> t.Tuple[GazetteerConfig, ProjectionCompiler]:
    """Validate a config and build a compiler against the live catalog."""
    config = GazetteerConfig.model_validate(config_data)
    catalog = {}
    for input_config in config.inputs:
        rows = connection.execute(f'DESCRIBE "{input_config.name}"').fetchall()
        catalog[input_config.name] = [row[0] for row in rows]
    return config, compiler_for(config, catalog)


def compiler_for(config: GazetteerConfig, catalog: dict) -> ProjectionCompiler:
    return ProjectionCompiler(config, catalog)


def run_features(
    connection: duckdb.DuckDBPyConnection,
    compiler: ProjectionCompiler,
    config: GazetteerConfig,
) -> t.Dict[str, dict]:
    """Run all feature queries and index the rows by identifier."""
    results = {}
    for feature in config.features:
        for identifier, type_, attributes, geometry in connection.execute(
            compiler.feature_query(feature)
        ).fetchall():
            results[identifier] = {
                "type": type_,
                "attributes": json.loads(attributes),
                "geometry": geometry,
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


def input_declaration(name: str) -> dict:
    """A tabular input declaration; the staged table is created in the test."""
    return {
        "name": name,
        "path": f"{name}.csv",
        "file": f"{name}.csv",
        "delimiter": ",",
    }


@pytest.fixture
def connection():
    con = duckdb.connect()
    con.load_extension("spatial")
    yield con
    con.close()


@pytest.mark.unit
class TestBasicProjection:
    """Test projection of a single input into features and names."""

    def make_places(self, connection):
        connection.execute(
            "CREATE TABLE places (id INTEGER, name VARCHAR, population INTEGER)"
        )
        connection.execute(
            "INSERT INTO places VALUES " "(1, 'Paris', 2100000), (2, 'Berlin', 3600000)"
        )

    def config_data(self, **feature_overrides) -> dict:
        feature = {
            "type": "place",
            "from": "places",
            "identifier": "id",
            "names": [{"column": "name"}],
            "attributes": ["name", "population"],
        }
        feature.update(feature_overrides)
        return {
            "name": "testgaz",
            "inputs": [input_declaration("places")],
            "features": [feature],
        }

    def test_projects_features_with_json_attributes(self, connection):
        """Each row becomes a feature with its attributes as JSON."""
        self.make_places(connection)
        config, compiler = build_compiler(connection, self.config_data())

        features = run_features(connection, compiler, config)

        assert features["1"]["type"] == "place"
        assert features["1"]["attributes"] == {"name": "Paris", "population": 2100000}
        assert features["2"]["attributes"] == {"name": "Berlin", "population": 3600000}

    def test_projects_names(self, connection):
        """Name columns produce (identifier, text) rows."""
        self.make_places(connection)
        config, compiler = build_compiler(connection, self.config_data())

        names = run_names(connection, compiler, config)

        assert names == {"1": {"Paris"}, "2": {"Berlin"}}

    def test_name_expression(self, connection):
        """Names can be scalar SQL expressions."""
        self.make_places(connection)
        config, compiler = build_compiler(
            connection,
            self.config_data(names=[{"expression": "upper(name)"}]),
        )

        names = run_names(connection, compiler, config)

        assert names == {"1": {"PARIS"}, "2": {"BERLIN"}}

    def test_attribute_expression(self, connection):
        """Attributes can be scalar SQL expressions."""
        self.make_places(connection)
        config, compiler = build_compiler(
            connection,
            self.config_data(
                attributes=[{"name": "shout", "expression": "upper(name)"}]
            ),
        )

        features = run_features(connection, compiler, config)

        assert features["1"]["attributes"] == {"shout": "PARIS"}

    def test_rows_with_null_identifier_are_dropped(self, connection):
        """Rows without an identifier value produce no feature."""
        self.make_places(connection)
        connection.execute("INSERT INTO places VALUES (NULL, 'Ghost', 0)")
        config, compiler = build_compiler(connection, self.config_data())

        features = run_features(connection, compiler, config)

        assert set(features) == {"1", "2"}

    def test_empty_and_null_names_are_dropped(self, connection):
        """NULL or blank name values produce no name rows."""
        self.make_places(connection)
        connection.execute("INSERT INTO places VALUES (3, NULL, 0), (4, '  ', 0)")
        config, compiler = build_compiler(connection, self.config_data())

        names = run_names(connection, compiler, config)

        assert set(names) == {"1", "2"}

    def test_unknown_attribute_column_raises_with_hint(self, connection):
        """Unknown attribute columns fail compilation with the available columns."""
        self.make_places(connection)
        config, compiler = build_compiler(
            connection, self.config_data(attributes=["nonexistent"])
        )

        with pytest.raises(CompileError, match="Available columns"):
            compiler.feature_query(config.features[0])

    def test_unknown_name_column_raises(self, connection):
        """Unknown name columns fail compilation."""
        self.make_places(connection)
        config, compiler = build_compiler(
            connection, self.config_data(names=[{"column": "nonexistent"}])
        )

        with pytest.raises(CompileError, match="unknown column 'nonexistent'"):
            compiler.name_queries(config.features[0])


@pytest.mark.unit
class TestSplitNames:
    """Test splitting multi-value name fields."""

    def test_split_produces_one_name_per_value(self, connection):
        """A comma-separated field is split into individual trimmed names."""
        connection.execute("CREATE TABLE places (id INTEGER, alternates VARCHAR)")
        connection.execute(
            "INSERT INTO places VALUES (1, 'Wien, Vienna , Vindobona'), (2, '')"
        )
        config, compiler = build_compiler(
            connection,
            {
                "name": "testgaz",
                "inputs": [input_declaration("places")],
                "features": [
                    {
                        "type": "place",
                        "from": "places",
                        "identifier": "id",
                        "names": [{"column": "alternates", "split": ","}],
                    }
                ],
            },
        )

        names = run_names(connection, compiler, config)

        assert names == {"1": {"Wien", "Vienna", "Vindobona"}}


@pytest.mark.unit
class TestRelatedInputNames:
    """Test one-to-many names from a related input."""

    def test_names_come_from_related_table(self, connection):
        """A separate names table keyed by identifier is first-class."""
        connection.execute("CREATE TABLE places (id INTEGER, name VARCHAR)")
        connection.execute("INSERT INTO places VALUES (1, 'Roma')")
        connection.execute("CREATE TABLE alt_names (place_id INTEGER, alt VARCHAR)")
        connection.execute(
            "INSERT INTO alt_names VALUES (1, 'Rome'), (1, 'Rom'), (99, 'Elsewhere')"
        )
        config, compiler = build_compiler(
            connection,
            {
                "name": "testgaz",
                "inputs": [
                    input_declaration("places"),
                    input_declaration("alt_names"),
                ],
                "features": [
                    {
                        "type": "place",
                        "from": "places",
                        "identifier": "id",
                        "names": [
                            {"column": "name"},
                            {"from": "alt_names", "key": "place_id", "column": "alt"},
                        ],
                    }
                ],
            },
        )

        names = run_names(connection, compiler, config)

        # Names of identifiers not produced by any feature block ("99") are
        # emitted here but dropped later by the builder's join.
        assert names["1"] == {"Roma", "Rome", "Rom"}

    def test_unknown_related_key_raises(self, connection):
        """The key must be a column of the related input."""
        connection.execute("CREATE TABLE places (id INTEGER, name VARCHAR)")
        connection.execute("CREATE TABLE alt_names (place_id INTEGER, alt VARCHAR)")
        config, compiler = build_compiler(
            connection,
            {
                "name": "testgaz",
                "inputs": [
                    input_declaration("places"),
                    input_declaration("alt_names"),
                ],
                "features": [
                    {
                        "type": "place",
                        "from": "places",
                        "identifier": "id",
                        "names": [
                            {"from": "alt_names", "key": "wrong", "column": "alt"}
                        ],
                    }
                ],
            },
        )

        with pytest.raises(CompileError, match="key 'wrong'"):
            compiler.name_queries(config.features[0])


@pytest.mark.unit
class TestMergePolicies:
    """Test explicit duplicate-identifier merge policies."""

    def make_duplicates(self, connection):
        connection.execute(
            "CREATE TABLE places (id INTEGER, name VARCHAR, height INTEGER)"
        )
        connection.execute(
            "INSERT INTO places VALUES "
            "(1, 'North Peak', 800), (1, 'South Peak', 1200), (2, 'Valley', 300)"
        )

    def config_data(self, merge=None, attributes=None) -> dict:
        feature = {
            "type": "peak",
            "from": "places",
            "identifier": "id",
            "names": [{"column": "name"}],
            "attributes": attributes or ["name", "height"],
        }
        if merge:
            feature["merge"] = merge
        return {
            "name": "testgaz",
            "inputs": [input_declaration("places")],
            "features": [feature],
        }

    def test_duplicate_rows_merge_into_one_feature(self, connection):
        """Rows sharing an identifier become a single feature."""
        self.make_duplicates(connection)
        config, compiler = build_compiler(connection, self.config_data())

        features = run_features(connection, compiler, config)

        assert set(features) == {"1", "2"}

    def test_names_are_collected_across_duplicates(self, connection):
        """All names of duplicate rows are kept."""
        self.make_duplicates(connection)
        config, compiler = build_compiler(connection, self.config_data())

        names = run_names(connection, compiler, config)

        assert names["1"] == {"North Peak", "South Peak"}

    def test_attributes_default_to_first_row(self, connection):
        """The default policy keeps the first row's attribute values."""
        self.make_duplicates(connection)
        config, compiler = build_compiler(connection, self.config_data())

        features = run_features(connection, compiler, config)

        assert features["1"]["attributes"]["name"] == "North Peak"
        assert features["1"]["attributes"]["height"] == 800

    def test_attribute_policy_min_max(self, connection):
        """min/max policies aggregate across duplicate rows."""
        self.make_duplicates(connection)
        config, compiler = build_compiler(
            connection,
            self.config_data(
                attributes=[
                    {"name": "lowest", "column": "height", "merge": "min"},
                    {"name": "highest", "column": "height", "merge": "max"},
                ]
            ),
        )

        features = run_features(connection, compiler, config)

        assert features["1"]["attributes"] == {"lowest": 800, "highest": 1200}

    def test_block_level_attribute_policy(self, connection):
        """The block-level policy applies to attributes without their own."""
        self.make_duplicates(connection)
        config, compiler = build_compiler(
            connection, self.config_data(merge={"attributes": "max"})
        )

        features = run_features(connection, compiler, config)

        assert features["1"]["attributes"]["height"] == 1200


@pytest.mark.unit
class TestGeometry:
    """Test geometry projection and merging."""

    def test_point_geometry_from_coordinates(self, connection):
        """lon/lat columns become WKB point geometries."""
        connection.execute(
            "CREATE TABLE places (id INTEGER, name VARCHAR, lon DOUBLE, lat DOUBLE)"
        )
        connection.execute(
            "INSERT INTO places VALUES (1, 'A', 1.5, 42.5), (2, 'B', NULL, NULL)"
        )
        config, compiler = build_compiler(
            connection,
            {
                "name": "testgaz",
                "inputs": [input_declaration("places")],
                "features": [
                    {
                        "type": "place",
                        "from": "places",
                        "identifier": "id",
                        "names": [{"column": "name"}],
                        "geometry": {"point": {"lon": "lon", "lat": "lat"}},
                    }
                ],
            },
        )

        features = run_features(connection, compiler, config)

        from shapely import wkb

        point = wkb.loads(bytes(features["1"]["geometry"]))
        assert (point.x, point.y) == (1.5, 42.5)
        assert features["2"]["geometry"] is None

    def test_geometry_union_merge(self, connection):
        """The union policy combines geometries of duplicate rows."""
        connection.execute(
            "CREATE TABLE places (id INTEGER, name VARCHAR, geometry GEOMETRY)"
        )
        connection.execute(
            "INSERT INTO places VALUES "
            "(1, 'Multi', ST_Point(0, 0)), (1, 'Multi', ST_Point(1, 1))"
        )
        config, compiler = build_compiler(
            connection,
            {
                "name": "testgaz",
                "inputs": [
                    {"name": "places", "path": "places.shp", "file": "places.shp"}
                ],
                "features": [
                    {
                        "type": "place",
                        "from": "places",
                        "identifier": "id",
                        "names": [{"column": "name"}],
                        "geometry": {"column": "geometry"},
                        "merge": {"geometry": "union"},
                    }
                ],
            },
        )

        features = run_features(connection, compiler, config)

        from shapely import wkb

        union = wkb.loads(bytes(features["1"]["geometry"]))
        assert union.geom_type == "MultiPoint"
        assert len(union.geoms) == 2

    def test_geometry_is_reprojected_to_gazetteer_crs(self, connection):
        """Geometries in a different CRS are transformed at build time."""
        connection.execute(
            "CREATE TABLE places (id INTEGER, name VARCHAR, geometry GEOMETRY)"
        )
        # LV95 coordinates of Bern
        connection.execute(
            "INSERT INTO places VALUES (1, 'Bern', ST_Point(2600000, 1200000))"
        )
        config, compiler = build_compiler(
            connection,
            {
                "name": "testgaz",
                "crs": "EPSG:4326",
                "inputs": [
                    {"name": "places", "path": "places.shp", "file": "places.shp"}
                ],
                "features": [
                    {
                        "type": "place",
                        "from": "places",
                        "identifier": "id",
                        "names": [{"column": "name"}],
                        "geometry": {"column": "geometry", "crs": "EPSG:2056"},
                    }
                ],
            },
        )

        features = run_features(connection, compiler, config)

        from shapely import wkb

        point = wkb.loads(bytes(features["1"]["geometry"]))
        assert point.x == pytest.approx(7.44, abs=0.05)
        assert point.y == pytest.approx(46.95, abs=0.05)


@pytest.mark.unit
class TestLookups:
    """Test lookup joins."""

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

    def test_lookup_value_becomes_attribute(self, connection):
        """Lookup values are available as attribute columns."""
        self.make_data(connection)
        config, compiler = build_compiler(
            connection,
            {
                "name": "testgaz",
                "inputs": [
                    input_declaration("places"),
                    input_declaration("countries"),
                ],
                "lookups": {
                    "country": {
                        "from": "countries",
                        "match": {"on": {"country_code": "code"}},
                        "values": {"country_name": "label"},
                    }
                },
                "features": [
                    {
                        "type": "place",
                        "from": "places",
                        "identifier": "id",
                        "names": [{"column": "name"}],
                        "lookups": ["country"],
                        "attributes": ["name", "country_name"],
                    }
                ],
            },
        )

        features = run_features(connection, compiler, config)

        assert features["1"]["attributes"]["country_name"] == "Switzerland"
        assert features["2"]["attributes"]["country_name"] is None

    def test_lookup_with_expression_key(self, connection):
        """The feature side of a match can be a scalar expression."""
        self.make_data(connection)
        config, compiler = build_compiler(
            connection,
            {
                "name": "testgaz",
                "inputs": [input_declaration("places"), input_declaration("admins")],
                "lookups": {
                    "admin": {
                        "from": "admins",
                        "match": {"on": {"country_code || '.' || admin_code": "code"}},
                        "values": {"admin_name": "label"},
                    }
                },
                "features": [
                    {
                        "type": "place",
                        "from": "places",
                        "identifier": "id",
                        "names": [{"column": "name"}],
                        "lookups": ["admin"],
                        "attributes": ["name", "admin_name"],
                    }
                ],
            },
        )

        features = run_features(connection, compiler, config)

        assert features["1"]["attributes"]["admin_name"] == "Canton of Bern"

    def test_lookup_chains_off_earlier_lookup_value(self, connection):
        """A lookup can match on a value produced by an earlier lookup."""
        connection.execute("CREATE TABLE places (id INTEGER, name VARCHAR, a VARCHAR)")
        connection.execute("INSERT INTO places VALUES (1, 'X', 'a1')")
        connection.execute("CREATE TABLE level1 (code VARCHAR, parent VARCHAR)")
        connection.execute("INSERT INTO level1 VALUES ('a1', 'b1')")
        connection.execute("CREATE TABLE level2 (code VARCHAR, label VARCHAR)")
        connection.execute("INSERT INTO level2 VALUES ('b1', 'Top level')")
        config, compiler = build_compiler(
            connection,
            {
                "name": "testgaz",
                "inputs": [
                    input_declaration("places"),
                    input_declaration("level1"),
                    input_declaration("level2"),
                ],
                "lookups": {
                    "first": {
                        "from": "level1",
                        "match": {"on": {"a": "code"}},
                        "values": {"parent_code": "parent"},
                    },
                    "second": {
                        "from": "level2",
                        "match": {"on": {"parent_code": "code"}},
                        "values": {"parent_label": "label"},
                    },
                },
                "features": [
                    {
                        "type": "place",
                        "from": "places",
                        "identifier": "id",
                        "names": [{"column": "name"}],
                        "lookups": ["first", "second"],
                        "attributes": ["parent_label"],
                    }
                ],
            },
        )

        features = run_features(connection, compiler, config)

        assert features["1"]["attributes"]["parent_label"] == "Top level"

    def test_spatial_lookup(self, connection):
        """Spatial lookups join the feature geometry against boundaries."""
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
            connection,
            {
                "name": "testgaz",
                "inputs": [
                    input_declaration("places"),
                    {"name": "zones", "path": "zones.shp", "file": "zones.shp"},
                ],
                "lookups": {
                    "zone": {
                        "from": "zones",
                        "match": {"spatial": "within"},
                        "values": {"zone_name": "zone_name"},
                    }
                },
                "features": [
                    {
                        "type": "place",
                        "from": "places",
                        "identifier": "id",
                        "names": [{"column": "name"}],
                        "geometry": {"point": {"lon": "lon", "lat": "lat"}},
                        "lookups": ["zone"],
                        "attributes": ["zone_name"],
                    }
                ],
            },
        )

        features = run_features(connection, compiler, config)

        assert features["1"]["attributes"]["zone_name"] == "Unit Square"
        assert features["2"]["attributes"]["zone_name"] is None

    def test_lookup_value_shadows_base_column(self, connection):
        """A lookup value with the same name replaces the input's column."""
        connection.execute(
            "CREATE TABLE places (id INTEGER, name VARCHAR, label VARCHAR)"
        )
        connection.execute("INSERT INTO places VALUES (1, 'X', 'base label')")
        connection.execute("CREATE TABLE extra (place_id INTEGER, label VARCHAR)")
        connection.execute("INSERT INTO extra VALUES (1, 'lookup label')")
        config, compiler = build_compiler(
            connection,
            {
                "name": "testgaz",
                "inputs": [input_declaration("places"), input_declaration("extra")],
                "lookups": {
                    "enrich": {
                        "from": "extra",
                        "match": {"on": {"id": "place_id"}},
                        "values": {"label": "label"},
                    }
                },
                "features": [
                    {
                        "type": "place",
                        "from": "places",
                        "identifier": "id",
                        "names": [{"column": "name"}],
                        "lookups": ["enrich"],
                        "attributes": ["label"],
                    }
                ],
            },
        )

        features = run_features(connection, compiler, config)

        assert features["1"]["attributes"]["label"] == "lookup label"

    def test_unknown_lookup_value_column_raises(self, connection):
        """Lookup values must reference columns of the lookup input."""
        self.make_data(connection)
        config, compiler = build_compiler(
            connection,
            {
                "name": "testgaz",
                "inputs": [
                    input_declaration("places"),
                    input_declaration("countries"),
                ],
                "lookups": {
                    "country": {
                        "from": "countries",
                        "match": {"on": {"country_code": "code"}},
                        "values": {"country_name": "nonexistent"},
                    }
                },
                "features": [
                    {
                        "type": "place",
                        "from": "places",
                        "identifier": "id",
                        "names": [{"column": "name"}],
                        "lookups": ["country"],
                    }
                ],
            },
        )

        with pytest.raises(CompileError, match="unknown column 'nonexistent'"):
            compiler.feature_query(config.features[0])

    def test_unresolvable_match_key_raises(self, connection):
        """A match key that is neither a column nor a lookup value fails."""
        self.make_data(connection)
        config, compiler = build_compiler(
            connection,
            {
                "name": "testgaz",
                "inputs": [
                    input_declaration("places"),
                    input_declaration("countries"),
                ],
                "lookups": {
                    "country": {
                        "from": "countries",
                        "match": {"on": {"nonexistent": "code"}},
                        "values": {"country_name": "label"},
                    }
                },
                "features": [
                    {
                        "type": "place",
                        "from": "places",
                        "identifier": "id",
                        "names": [{"column": "name"}],
                        "lookups": ["country"],
                    }
                ],
            },
        )

        with pytest.raises(CompileError, match="matches\\s+on 'nonexistent'"):
            compiler.feature_query(config.features[0])


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
