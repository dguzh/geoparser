"""
Unit tests for geoparser/gazetteer/config/schema.py

Tests validation of the declarative gazetteer configuration schema.
"""

import textwrap

import pytest
from pydantic import ValidationError

from geoparser.gazetteer.config import (
    AttributeMerge,
    GazetteerConfig,
    GeometryMerge,
    SpatialPredicate,
)


def minimal_config(**overrides) -> dict:
    """Return a minimal valid configuration, optionally overridden."""
    config = {
        "name": "testgaz",
        "inputs": [
            {
                "name": "places",
                "path": "data/places.csv",
                "file": "places.csv",
                "delimiter": ",",
            }
        ],
        "features": [
            {
                "type": "place",
                "from": "places",
                "identifier": "id",
                "names": [{"column": "name"}],
            }
        ],
    }
    config.update(overrides)
    return config


@pytest.mark.unit
class TestGazetteerConfigValidation:
    """Test top-level configuration validation."""

    def test_minimal_config_is_valid(self):
        """A minimal config with one input and one feature validates."""
        config = GazetteerConfig.model_validate(minimal_config())

        assert config.name == "testgaz"
        assert config.crs == "EPSG:4326"
        assert len(config.inputs) == 1
        assert len(config.features) == 1

    def test_rejects_invalid_gazetteer_name(self):
        """Gazetteer names are restricted to a safe character set."""
        with pytest.raises(ValidationError, match="must contain only"):
            GazetteerConfig.model_validate(minimal_config(name="bad name!"))

    def test_requires_at_least_one_input(self):
        """A gazetteer without inputs is rejected."""
        with pytest.raises(ValidationError, match="at least one input"):
            GazetteerConfig.model_validate(minimal_config(inputs=[]))

    def test_requires_at_least_one_feature(self):
        """A gazetteer without feature blocks is rejected."""
        with pytest.raises(ValidationError, match="at least one feature"):
            GazetteerConfig.model_validate(minimal_config(features=[]))

    def test_rejects_duplicate_input_names(self):
        """Two inputs with the same name are rejected."""
        data = minimal_config()
        data["inputs"].append(dict(data["inputs"][0]))

        with pytest.raises(ValidationError, match="Duplicate input names"):
            GazetteerConfig.model_validate(data)

    def test_rejects_feature_referencing_unknown_input(self):
        """A feature block must project from a declared input."""
        data = minimal_config()
        data["features"][0]["from"] = "nowhere"

        with pytest.raises(ValidationError, match="unknown input 'nowhere'"):
            GazetteerConfig.model_validate(data)

    def test_rejects_feature_referencing_unknown_lookup(self):
        """A feature block can only use declared lookups."""
        data = minimal_config()
        data["features"][0]["lookups"] = ["missing"]

        with pytest.raises(ValidationError, match="unknown lookup 'missing'"):
            GazetteerConfig.model_validate(data)

    def test_rejects_lookup_referencing_unknown_input(self):
        """A lookup must join against a declared input."""
        data = minimal_config()
        data["lookups"] = {
            "extra": {
                "from": "nowhere",
                "match": {"on": {"id": "id"}},
                "values": {"extra_name": "name"},
            }
        }

        with pytest.raises(ValidationError, match="unknown input 'nowhere'"):
            GazetteerConfig.model_validate(data)

    def test_rejects_lookups_exposing_same_value_name(self):
        """Two lookups on one feature must not expose the same value name."""
        data = minimal_config()
        lookup = {
            "from": "places",
            "match": {"on": {"id": "id"}},
            "values": {"clash": "name"},
        }
        data["lookups"] = {"first": dict(lookup), "second": dict(lookup)}
        data["features"][0]["lookups"] = ["first", "second"]

        with pytest.raises(
            ValidationError, match="both\\s+expose a value named 'clash'"
        ):
            GazetteerConfig.model_validate(data)


@pytest.mark.unit
class TestInputConfigValidation:
    """Test input validation."""

    def test_requires_exactly_one_of_url_or_path(self):
        """An input must be either remote (url) or local (path)."""
        data = minimal_config()
        data["inputs"][0]["url"] = "https://example.com/places.zip"

        with pytest.raises(ValidationError, match="exactly one of 'url' or 'path'"):
            GazetteerConfig.model_validate(data)

        del data["inputs"][0]["url"]
        del data["inputs"][0]["path"]

        with pytest.raises(ValidationError, match="exactly one of 'url' or 'path'"):
            GazetteerConfig.model_validate(data)

    def test_rejects_tabular_options_on_spatial_input(self):
        """Options like 'columns' require a delimiter (tabular input)."""
        data = minimal_config()
        data["inputs"][0].pop("delimiter")
        data["inputs"][0]["columns"] = [{"name": "id"}]

        with pytest.raises(ValidationError, match="only valid for tabular"):
            GazetteerConfig.model_validate(data)

    def test_rejects_crs_on_tabular_input(self):
        """The input-level CRS is reserved for spatial inputs."""
        data = minimal_config()
        data["inputs"][0]["crs"] = "EPSG:2056"

        with pytest.raises(ValidationError, match="only valid for spatial"):
            GazetteerConfig.model_validate(data)

    def test_rejects_duplicate_column_names(self):
        """Declared columns of a tabular input must be unique."""
        data = minimal_config()
        data["inputs"][0]["columns"] = [{"name": "id"}, {"name": "id"}]

        with pytest.raises(ValidationError, match="duplicate column names"):
            GazetteerConfig.model_validate(data)

    def test_rejects_invalid_input_name(self):
        """Input names must be valid identifiers."""
        data = minimal_config()
        data["inputs"][0]["name"] = "has space"
        data["features"][0]["from"] = "has space"

        with pytest.raises(ValidationError, match="must start with a letter"):
            GazetteerConfig.model_validate(data)


@pytest.mark.unit
class TestLookupConfigValidation:
    """Test lookup validation."""

    def base_with_lookup(self, match: dict) -> dict:
        data = minimal_config()
        data["lookups"] = {
            "extra": {
                "from": "places",
                "match": match,
                "values": {"extra_name": "name"},
            }
        }
        return data

    def test_accepts_equality_match(self):
        """A lookup can match on column equality."""
        config = GazetteerConfig.model_validate(
            self.base_with_lookup({"on": {"code": "code"}})
        )

        assert config.lookups["extra"].match.on == {"code": "code"}

    def test_accepts_spatial_match(self):
        """A lookup can match spatially."""
        config = GazetteerConfig.model_validate(
            self.base_with_lookup({"spatial": "within", "using": "centroid"})
        )

        assert config.lookups["extra"].match.spatial == SpatialPredicate.WITHIN

    def test_rejects_match_with_both_on_and_spatial(self):
        """'on' and 'spatial' are mutually exclusive."""
        with pytest.raises(ValidationError, match="exactly one of 'on' or 'spatial'"):
            GazetteerConfig.model_validate(
                self.base_with_lookup({"on": {"a": "b"}, "spatial": "within"})
            )

    def test_rejects_using_without_spatial(self):
        """'using' only applies to spatial matches."""
        with pytest.raises(ValidationError, match="only valid for spatial"):
            GazetteerConfig.model_validate(
                self.base_with_lookup({"on": {"a": "b"}, "using": "centroid"})
            )

    def test_rejects_lookup_without_values(self):
        """A lookup must expose at least one value."""
        data = minimal_config()
        data["lookups"] = {
            "extra": {"from": "places", "match": {"on": {"a": "b"}}, "values": {}}
        }

        with pytest.raises(ValidationError, match="at least one value"):
            GazetteerConfig.model_validate(data)

    def test_yaml_bare_on_key_is_coerced(self):
        """YAML 1.1 parses the bare key 'on' as True; it must still work."""
        yaml_text = textwrap.dedent(
            """
            name: testgaz
            inputs:
              - name: places
                path: data/places.csv
                file: places.csv
                delimiter: ","
            lookups:
              extra:
                from: places
                match: { on: { code: code } }
                values: { extra_name: name }
            features:
              - type: place
                from: places
                identifier: id
                names: [{ column: name }]
                lookups: [extra]
            """
        )
        import yaml

        config = GazetteerConfig.model_validate(yaml.safe_load(yaml_text))

        assert config.lookups["extra"].match.on == {"code": "code"}


@pytest.mark.unit
class TestFeatureConfigValidation:
    """Test feature block validation."""

    def test_requires_at_least_one_name(self):
        """A feature must define at least one name."""
        data = minimal_config()
        data["features"][0]["names"] = []

        with pytest.raises(ValidationError, match="at least one name"):
            GazetteerConfig.model_validate(data)

    def test_name_requires_exactly_one_of_column_or_expression(self):
        """A name is either a column or an expression."""
        data = minimal_config()
        data["features"][0]["names"] = [{"column": "name", "expression": "name"}]

        with pytest.raises(
            ValidationError, match="exactly one of 'column' or 'expression'"
        ):
            GazetteerConfig.model_validate(data)

    def test_related_name_requires_from_and_key(self):
        """Names from a related input need both 'from' and 'key'."""
        data = minimal_config()
        data["features"][0]["names"] = [{"column": "name", "from": "places"}]

        with pytest.raises(ValidationError, match="both 'from' and 'key'"):
            GazetteerConfig.model_validate(data)

    def test_related_name_must_reference_known_input(self):
        """The related input of a name must be declared."""
        data = minimal_config()
        data["features"][0]["names"] = [
            {"column": "name", "from": "nowhere", "key": "id"}
        ]

        with pytest.raises(ValidationError, match="unknown\\s+input 'nowhere'"):
            GazetteerConfig.model_validate(data)

    def test_geometry_requires_exactly_one_of_column_or_point(self):
        """A geometry is either a column or a lon/lat point."""
        data = minimal_config()
        data["features"][0]["geometry"] = {
            "column": "geometry",
            "point": {"lon": "lon", "lat": "lat"},
        }

        with pytest.raises(ValidationError, match="exactly one of 'column' or 'point'"):
            GazetteerConfig.model_validate(data)

    def test_attribute_shorthand_expands_to_column(self):
        """The string shorthand maps an attribute name to a same-named column."""
        data = minimal_config()
        data["features"][0]["attributes"] = ["population"]

        config = GazetteerConfig.model_validate(data)

        attribute = config.features[0].attributes[0]
        assert attribute.name == "population"
        assert attribute.column == "population"

    def test_rejects_duplicate_attribute_names(self):
        """Attribute names must be unique within a feature."""
        data = minimal_config()
        data["features"][0]["attributes"] = ["population", "population"]

        with pytest.raises(ValidationError, match="duplicate attribute names"):
            GazetteerConfig.model_validate(data)

    def test_rejects_attribute_with_column_and_expression(self):
        """An attribute cannot be both a column and an expression."""
        data = minimal_config()
        data["features"][0]["attributes"] = [
            {"name": "x", "column": "a", "expression": "b"}
        ]

        with pytest.raises(ValidationError, match="both 'column' and 'expression'"):
            GazetteerConfig.model_validate(data)

    def test_rejects_duplicate_lookups(self):
        """A feature cannot list the same lookup twice."""
        data = minimal_config()
        data["lookups"] = {
            "extra": {
                "from": "places",
                "match": {"on": {"a": "b"}},
                "values": {"v": "name"},
            }
        }
        data["features"][0]["lookups"] = ["extra", "extra"]

        with pytest.raises(ValidationError, match="duplicate lookups"):
            GazetteerConfig.model_validate(data)

    def test_merge_policies_parse(self):
        """Merge policies are parsed into their enums."""
        data = minimal_config()
        data["features"][0]["merge"] = {"geometry": "union", "attributes": "max"}

        config = GazetteerConfig.model_validate(data)

        assert config.features[0].merge.geometry == GeometryMerge.UNION
        assert config.features[0].merge.attributes == AttributeMerge.MAX

    def test_merge_defaults_to_first(self):
        """Without an explicit policy, duplicates keep the first row's values."""
        config = GazetteerConfig.model_validate(minimal_config())

        assert config.features[0].merge.geometry == GeometryMerge.FIRST
        assert config.features[0].merge.attributes == AttributeMerge.FIRST


@pytest.mark.unit
class TestFromYaml:
    """Test loading configs from YAML files."""

    def test_loads_and_resolves_relative_paths(self, tmp_path):
        """Relative input paths resolve against the config file's directory."""
        config_file = tmp_path / "gaz.yaml"
        config_file.write_text(
            textwrap.dedent(
                """
                name: testgaz
                inputs:
                  - name: places
                    path: data/places.csv
                    file: places.csv
                    delimiter: ","
                features:
                  - type: place
                    from: places
                    identifier: id
                    names: [{ column: name }]
                """
            )
        )

        config = GazetteerConfig.from_yaml(config_file)

        assert config.inputs[0].path == str(tmp_path / "data" / "places.csv")

    def test_absolute_paths_are_kept(self, tmp_path):
        """Absolute input paths are left untouched."""
        config_file = tmp_path / "gaz.yaml"
        config_file.write_text(
            textwrap.dedent(
                """
                name: testgaz
                inputs:
                  - name: places
                    path: /data/places.csv
                    file: places.csv
                    delimiter: ","
                features:
                  - type: place
                    from: places
                    identifier: id
                    names: [{ column: name }]
                """
            )
        )

        config = GazetteerConfig.from_yaml(config_file)

        assert config.inputs[0].path == "/data/places.csv"
