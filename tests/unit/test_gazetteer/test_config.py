"""
Unit tests for geoparser/gazetteer/config/schema.py

Tests validation of the declarative gazetteer configuration schema.
"""

import textwrap

import pytest
from pydantic import ValidationError

from geoparser.gazetteer.config import GazetteerConfig


def minimal_config(**overrides) -> dict:
    """Return a minimal valid configuration, optionally overridden."""
    config = {
        "name": "testgaz",
        "sources": [
            {
                "name": "places",
                "path": "data/places.csv",
                "file": "places.csv",
                "delimiter": ",",
                "attributes": [
                    {"name": "id", "type": "integer"},
                    {"name": "name", "type": "text"},
                ],
            }
        ],
        "features": [
            {
                "source": "places",
                "identifier": "id",
                "names": ["name"],
            }
        ],
    }
    config.update(overrides)
    return config


def spatial_source(**overrides) -> dict:
    """A spatial source declaration (no delimiter, one geometry attribute)."""
    data = {
        "name": "shape",
        "path": "data/shape.shp",
        "file": "shape.shp",
        "attributes": [
            {"name": "OGC_FID", "type": "integer"},
            {"name": "geometry", "type": "geometry"},
        ],
    }
    data.update(overrides)
    return data


@pytest.mark.unit
class TestGazetteerConfigValidation:
    """Test top-level configuration validation."""

    def test_minimal_config_is_valid(self):
        """A minimal config with one source and one feature validates."""
        config = GazetteerConfig.model_validate(minimal_config())

        assert config.name == "testgaz"
        assert config.crs == "EPSG:4326"
        assert len(config.sources) == 1
        assert len(config.features) == 1

    def test_rejects_invalid_gazetteer_name(self):
        """Gazetteer names are restricted to a safe character set."""
        with pytest.raises(ValidationError, match="must contain only"):
            GazetteerConfig.model_validate(minimal_config(name="bad name!"))

    def test_requires_at_least_one_source(self):
        """A gazetteer without sources is rejected."""
        with pytest.raises(ValidationError, match="at least one source"):
            GazetteerConfig.model_validate(minimal_config(sources=[]))

    def test_requires_at_least_one_feature(self):
        """A gazetteer without feature blocks is rejected."""
        with pytest.raises(ValidationError, match="at least one feature"):
            GazetteerConfig.model_validate(minimal_config(features=[]))

    def test_rejects_duplicate_source_names(self):
        """Two sources with the same name are rejected."""
        data = minimal_config()
        data["sources"].append(dict(data["sources"][0]))

        with pytest.raises(ValidationError, match="Duplicate source names"):
            GazetteerConfig.model_validate(data)

    def test_rejects_feature_referencing_unknown_source(self):
        """A feature block must project from a declared source."""
        data = minimal_config()
        data["features"][0]["source"] = "nowhere"

        with pytest.raises(ValidationError, match="unknown source 'nowhere'"):
            GazetteerConfig.model_validate(data)

    def test_rejects_two_feature_blocks_from_same_source(self):
        """Each source can back at most one feature block."""
        data = minimal_config()
        data["features"].append(dict(data["features"][0]))

        with pytest.raises(
            ValidationError, match="at most one feature block"
        ):
            GazetteerConfig.model_validate(data)


@pytest.mark.unit
class TestSourceConfigValidation:
    """Test source validation."""

    def test_requires_exactly_one_of_url_or_path(self):
        """A source must be either remote (url) or local (path)."""
        data = minimal_config()
        data["sources"][0]["url"] = "https://example.com/places.zip"

        with pytest.raises(ValidationError, match="exactly one of 'url' or 'path'"):
            GazetteerConfig.model_validate(data)

        del data["sources"][0]["url"]
        del data["sources"][0]["path"]

        with pytest.raises(ValidationError, match="exactly one of 'url' or 'path'"):
            GazetteerConfig.model_validate(data)

    def test_requires_at_least_one_attribute(self):
        """Every source must declare its attributes."""
        data = minimal_config()
        data["sources"][0]["attributes"] = []

        with pytest.raises(ValidationError, match="at least one attribute"):
            GazetteerConfig.model_validate(data)

    def test_rejects_duplicate_attribute_names(self):
        """Declared attributes of a source must be unique."""
        data = minimal_config()
        data["sources"][0]["attributes"] = [
            {"name": "id", "type": "integer"},
            {"name": "id", "type": "integer"},
        ]

        with pytest.raises(ValidationError, match="duplicate attribute names"):
            GazetteerConfig.model_validate(data)

    def test_rejects_geometry_attribute_on_tabular_source(self):
        """Tabular sources have no geometry, so they cannot declare one."""
        data = minimal_config()
        data["sources"][0]["attributes"].append(
            {"name": "geometry", "type": "geometry"}
        )

        with pytest.raises(
            ValidationError, match="tabular sources cannot declare a geometry"
        ):
            GazetteerConfig.model_validate(data)

    def test_spatial_source_requires_exactly_one_geometry_attribute(self):
        """A spatial source must declare exactly one geometry attribute."""
        data = minimal_config()
        data["sources"].append(
            spatial_source(attributes=[{"name": "OGC_FID", "type": "integer"}])
        )

        with pytest.raises(
            ValidationError, match="exactly one geometry attribute"
        ):
            GazetteerConfig.model_validate(data)

    def test_spatial_geometry_attribute_must_be_named_geometry(self):
        """The geometry attribute of a spatial source must be named 'geometry'."""
        data = minimal_config()
        data["sources"].append(
            spatial_source(
                attributes=[
                    {"name": "OGC_FID", "type": "integer"},
                    {"name": "geom", "type": "geometry"},
                ]
            )
        )

        with pytest.raises(ValidationError, match="must be named 'geometry'"):
            GazetteerConfig.model_validate(data)

    def test_rejects_tabular_options_on_spatial_source(self):
        """Options like 'quote' require a delimiter (tabular source)."""
        data = minimal_config()
        data["sources"].append(spatial_source(quote=""))

        with pytest.raises(ValidationError, match="only valid for tabular"):
            GazetteerConfig.model_validate(data)

    def test_crs_is_allowed_on_any_source(self):
        """The CRS declares a source's coordinate system and is always allowed."""
        data = minimal_config()
        data["sources"][0]["crs"] = "EPSG:2056"

        config = GazetteerConfig.model_validate(data)

        assert config.sources[0].crs == "EPSG:2056"

    def test_rejects_invalid_source_name(self):
        """Source names must be valid identifiers."""
        data = minimal_config()
        data["sources"][0]["name"] = "has space"
        data["features"][0]["source"] = "has space"

        with pytest.raises(ValidationError, match="must start with a letter"):
            GazetteerConfig.model_validate(data)


@pytest.mark.unit
class TestJoinConfigValidation:
    """Test that joins are raw SQL join clauses."""

    def test_defaults_to_no_joins(self):
        """A feature block without joins has an empty join list."""
        config = GazetteerConfig.model_validate(minimal_config())

        assert config.features[0].joins == []

    def test_accepts_raw_sql_join_clauses(self):
        """Joins are stored verbatim as SQL join clauses."""
        data = minimal_config()
        data["sources"].append(
            {
                "name": "extra",
                "path": "data/extra.csv",
                "file": "extra.csv",
                "delimiter": ",",
                "attributes": [
                    {"name": "eid", "type": "integer"},
                    {"name": "label", "type": "text"},
                ],
            }
        )
        data["features"][0]["joins"] = [
            "LEFT JOIN extra ON src.id = extra.eid"
        ]

        config = GazetteerConfig.model_validate(data)

        assert config.features[0].joins == ["LEFT JOIN extra ON src.id = extra.eid"]

    def test_rejects_blank_join_clause(self):
        """A blank join clause is rejected."""
        data = minimal_config()
        data["features"][0]["joins"] = ["   "]

        with pytest.raises(ValidationError, match="non-empty SQL join clause"):
            GazetteerConfig.model_validate(data)


@pytest.mark.unit
class TestNameConfigValidation:
    """Test name validation."""

    def test_name_is_a_plain_string(self):
        """A name is a column or expression string."""
        config = GazetteerConfig.model_validate(minimal_config())

        assert config.features[0].names[0] == "name"

    def test_requires_at_least_one_name(self):
        """A feature must define at least one name."""
        data = minimal_config()
        data["features"][0]["names"] = []

        with pytest.raises(ValidationError, match="at least one name"):
            GazetteerConfig.model_validate(data)

    def test_rejects_empty_name(self):
        """A blank name string is rejected."""
        data = minimal_config()
        data["features"][0]["names"] = ["  "]

        with pytest.raises(ValidationError, match="non-empty string"):
            GazetteerConfig.model_validate(data)


@pytest.mark.unit
class TestFeatureConfigValidation:
    """Test feature block validation."""

    def test_source_is_the_backing_source(self):
        """A feature's source in the artifact is the name of its source."""
        config = GazetteerConfig.model_validate(minimal_config())

        assert config.features[0].source == "places"

    def test_geometry_is_an_optional_value(self):
        """Geometry is a single column or expression, absent by default."""
        assert GazetteerConfig.model_validate(minimal_config()).features[0].geometry \
            is None

        data = minimal_config()
        data["features"][0]["geometry"] = "ST_Point(lon, lat)"
        config = GazetteerConfig.model_validate(data)

        assert config.features[0].geometry == "ST_Point(lon, lat)"

    def test_bare_column_is_stored_under_its_own_name(self):
        """A bare column reference is stored under its own name."""
        data = minimal_config()
        data["features"][0]["data"] = ["population"]

        config = GazetteerConfig.model_validate(data)

        assert config.features[0].data == ["population"]

    def test_data_alias_renames_the_key(self):
        """A trailing 'AS alias' renames the stored key."""
        data = minimal_config()
        data["features"][0]["data"] = ["population AS pop"]

        config = GazetteerConfig.model_validate(data)

        assert config.features[0].data == ["population AS pop"]

    def test_data_expression_requires_alias(self):
        """A data expression needs an alias to name the stored key."""
        data = minimal_config()
        data["features"][0]["data"] = ["upper(name)"]

        with pytest.raises(ValidationError, match="needs an alias"):
            GazetteerConfig.model_validate(data)

    def test_rejects_duplicate_data_keys(self):
        """Data keys must be unique within a feature."""
        data = minimal_config()
        data["features"][0]["data"] = ["population", "population"]

        with pytest.raises(ValidationError, match="duplicate data keys"):
            GazetteerConfig.model_validate(data)

    def test_rejects_duplicate_data_keys_via_alias(self):
        """Data keys must be unique even when one is renamed via an alias."""
        data = minimal_config()
        data["features"][0]["data"] = ["population", "population AS population"]

        with pytest.raises(ValidationError, match="duplicate data keys"):
            GazetteerConfig.model_validate(data)

    def test_rejects_blank_data_value(self):
        """A blank data entry is rejected."""
        data = minimal_config()
        data["features"][0]["data"] = ["   "]

        with pytest.raises(ValidationError, match="non-empty string"):
            GazetteerConfig.model_validate(data)


@pytest.mark.unit
class TestFromYaml:
    """Test loading configs from YAML files."""

    def test_loads_and_resolves_relative_paths(self, tmp_path):
        """Relative source paths resolve against the config file's directory."""
        config_file = tmp_path / "gaz.yaml"
        config_file.write_text(
            textwrap.dedent(
                """
                name: testgaz
                sources:
                  - name: places
                    path: data/places.csv
                    file: places.csv
                    delimiter: ","
                    attributes:
                      - name: id
                        type: integer
                      - name: name
                        type: text
                features:
                  - source: places
                    identifier: "id"
                    names:
                      - "name"
                """
            )
        )

        config = GazetteerConfig.from_yaml(config_file)

        assert config.sources[0].path == str(tmp_path / "data" / "places.csv")

    def test_absolute_paths_are_kept(self, tmp_path):
        """Absolute source paths are left untouched."""
        config_file = tmp_path / "gaz.yaml"
        config_file.write_text(
            textwrap.dedent(
                """
                name: testgaz
                sources:
                  - name: places
                    path: /data/places.csv
                    file: places.csv
                    delimiter: ","
                    attributes:
                      - name: id
                        type: integer
                      - name: name
                        type: text
                features:
                  - source: places
                    identifier: "id"
                    names:
                      - "name"
                """
            )
        )

        config = GazetteerConfig.from_yaml(config_file)

        assert config.sources[0].path == "/data/places.csv"
