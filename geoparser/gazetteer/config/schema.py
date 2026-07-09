"""
Declarative gazetteer configuration schema.

A gazetteer config describes how source files are projected into the canonical
feature store. It has three top-level concepts:

- ``inputs``: files to acquire and stage (transient; discarded after the build)
- ``lookups``: named, reusable many-to-one enrichments (attribute or spatial)
- ``features``: one block per entity type, describing how staged rows project
  into canonical features (identifier, names, geometry, attributes) with an
  explicit merge policy for duplicate identifiers

Configs are purely declarative: the only embedded SQL allowed are scalar
expressions (e.g. string manipulation for derived names or attributes).
"""

from __future__ import annotations

import re
import typing as t
from enum import Enum
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

# Gazetteer, input and lookup names are used as identifiers (file names, SQL
# table names, aliases), so they are restricted to a safe character set.
_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")
_IDENTIFIER_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

DEFAULT_CRS = "EPSG:4326"


class DataType(str, Enum):
    """Column data types for headerless tabular inputs."""

    TEXT = "text"
    INTEGER = "integer"
    REAL = "real"


class SpatialPredicate(str, Enum):
    """Spatial predicates supported by spatial lookups."""

    WITHIN = "within"
    INTERSECTS = "intersects"
    CONTAINS = "contains"


class GeometryTransform(str, Enum):
    """Transforms that can be applied to the feature geometry before matching."""

    CENTROID = "centroid"


class GeometryMerge(str, Enum):
    """How to combine geometries of rows sharing an identifier."""

    FIRST = "first"
    UNION = "union"


class AttributeMerge(str, Enum):
    """How to pick an attribute value among rows sharing an identifier."""

    FIRST = "first"
    MIN = "min"
    MAX = "max"


class ColumnDef(BaseModel):
    """Column definition for headerless tabular inputs."""

    name: str
    type: DataType = DataType.TEXT


class InputConfig(BaseModel):
    """
    A source file to acquire and stage.

    An input is tabular (delimited text) when ``delimiter`` is set, otherwise
    it is treated as a spatial file readable by DuckDB's spatial extension
    (shapefile, GeoPackage, GeoJSON, ...). Staged spatial inputs always expose
    their geometry under the column name ``geometry``.
    """

    name: str
    url: t.Optional[str] = None
    path: t.Optional[str] = None
    file: str

    # Tabular options
    delimiter: t.Optional[str] = None
    quote: t.Optional[str] = None
    skip_rows: int = 0
    columns: t.Optional[t.List[ColumnDef]] = None

    # Spatial options
    crs: t.Optional[str] = None

    @property
    def is_tabular(self) -> bool:
        """Whether this input is a delimited text file."""
        return self.delimiter is not None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not _IDENTIFIER_PATTERN.match(value):
            raise ValueError(
                f"Input name '{value}' must start with a letter or underscore and "
                "contain only letters, digits and underscores"
            )
        return value

    @model_validator(mode="after")
    def validate_input(self) -> "InputConfig":
        if bool(self.url) == bool(self.path):
            raise ValueError(
                f"Input '{self.name}' must define exactly one of 'url' or 'path'"
            )
        if not self.is_tabular:
            for field in ("quote", "columns"):
                if getattr(self, field) is not None:
                    raise ValueError(
                        f"Input '{self.name}': '{field}' is only valid for tabular "
                        "inputs (those with a 'delimiter')"
                    )
            if self.skip_rows:
                raise ValueError(
                    f"Input '{self.name}': 'skip_rows' is only valid for tabular inputs"
                )
        else:
            if self.crs is not None:
                raise ValueError(
                    f"Input '{self.name}': 'crs' is only valid for spatial inputs; "
                    "declare the coordinate system on the feature's 'geometry' instead"
                )
        if self.columns is not None:
            names = [column.name for column in self.columns]
            duplicates = {name for name in names if names.count(name) > 1}
            if duplicates:
                raise ValueError(
                    f"Input '{self.name}' has duplicate column names: "
                    f"{', '.join(sorted(duplicates))}"
                )
        return self


class MatchConfig(BaseModel):
    """
    How a lookup joins against its input.

    Exactly one of:

    - ``on``: equality match, mapping a column, a value produced by an
      earlier lookup, or a scalar SQL expression on the feature side to a
      column of the lookup input
    - ``spatial``: spatial match of the feature geometry against the lookup
      input's geometry, optionally reducing the feature geometry to its
      ``centroid`` first (via ``using``)
    """

    on: t.Optional[t.Dict[str, str]] = None
    spatial: t.Optional[SpatialPredicate] = None
    using: t.Optional[GeometryTransform] = None

    @model_validator(mode="before")
    @classmethod
    def coerce_yaml_on_key(cls, value: t.Any) -> t.Any:
        # YAML 1.1 parses the bare key "on" as boolean True; map it back
        if isinstance(value, dict) and True in value:
            value = {("on" if key is True else key): item for key, item in value.items()}
        return value

    @model_validator(mode="after")
    def validate_match(self) -> "MatchConfig":
        if bool(self.on) == bool(self.spatial):
            raise ValueError("A lookup match must define exactly one of 'on' or 'spatial'")
        if self.using is not None and self.spatial is None:
            raise ValueError("'using' is only valid for spatial matches")
        return self


class LookupConfig(BaseModel):
    """
    A named, reusable many-to-one enrichment.

    A lookup left-joins the feature rows against ``from`` and exposes the
    columns listed in ``values`` (mapping output name to a column of the
    lookup input) to the feature's names, attributes and later lookups.
    """

    from_: str = Field(alias="from")
    match: MatchConfig
    values: t.Dict[str, str]

    model_config = {"populate_by_name": True}

    @field_validator("values")
    @classmethod
    def validate_values(cls, value: t.Dict[str, str]) -> t.Dict[str, str]:
        if not value:
            raise ValueError("A lookup must expose at least one value")
        return value


class NameConfig(BaseModel):
    """
    A searchable name for a feature.

    Names can come from a column or scalar SQL expression over the feature's
    (enriched) rows, or from a related input (``from``/``key``) holding one
    name per row keyed by the feature identifier. ``split`` breaks multi-value
    fields into individual names.
    """

    column: t.Optional[str] = None
    expression: t.Optional[str] = None
    from_: t.Optional[str] = Field(default=None, alias="from")
    key: t.Optional[str] = None
    split: t.Optional[str] = None

    model_config = {"populate_by_name": True}

    @model_validator(mode="after")
    def validate_name(self) -> "NameConfig":
        if bool(self.column) == bool(self.expression):
            raise ValueError("A name must define exactly one of 'column' or 'expression'")
        if bool(self.from_) != bool(self.key):
            raise ValueError("Names from a related input require both 'from' and 'key'")
        return self


class PointConfig(BaseModel):
    """Point geometry built from coordinate columns (or scalar expressions)."""

    lon: str
    lat: str


class GeometryConfig(BaseModel):
    """
    The feature geometry.

    Either a geometry ``column`` of the (spatial) input or a ``point`` built
    from coordinate columns. ``crs`` declares the coordinate system of the
    source data; geometries are reprojected to the gazetteer CRS at build time.
    """

    column: t.Optional[str] = None
    point: t.Optional[PointConfig] = None
    crs: t.Optional[str] = None

    @model_validator(mode="after")
    def validate_geometry(self) -> "GeometryConfig":
        if bool(self.column) == bool(self.point is not None):
            raise ValueError(
                "A geometry must define exactly one of 'column' or 'point'"
            )
        return self


class MergeConfig(BaseModel):
    """
    Explicit policy for rows sharing an identifier.

    Names are always collected across duplicate rows. ``geometry`` selects the
    first geometry or the union of all geometries; ``attributes`` sets the
    default policy for attribute values (overridable per attribute).
    """

    geometry: GeometryMerge = GeometryMerge.FIRST
    attributes: AttributeMerge = AttributeMerge.FIRST


class AttributeConfig(BaseModel):
    """
    An attribute stored in the feature's JSON attributes object.

    The shorthand string form ``"NAME"`` is equivalent to
    ``{name: NAME, column: NAME}``, where the column may also be a value
    exposed by one of the feature's lookups.
    """

    name: str
    column: t.Optional[str] = None
    expression: t.Optional[str] = None
    merge: t.Optional[AttributeMerge] = None

    @model_validator(mode="before")
    @classmethod
    def coerce_shorthand(cls, value: t.Any) -> t.Any:
        if isinstance(value, str):
            return {"name": value, "column": value}
        return value

    @model_validator(mode="after")
    def validate_attribute(self) -> "AttributeConfig":
        if self.column and self.expression:
            raise ValueError(
                f"Attribute '{self.name}' cannot define both 'column' and 'expression'"
            )
        if not self.column and not self.expression:
            self.column = self.name
        return self


class FeatureConfig(BaseModel):
    """
    Projection of an input into canonical features of one entity type.

    Rows of ``from`` (enriched by ``lookups``) are grouped by ``identifier``
    and merged according to ``merge``; each group becomes one feature with the
    listed names, geometry and attributes.
    """

    type: str
    from_: str = Field(alias="from")
    identifier: str
    merge: MergeConfig = Field(default_factory=MergeConfig)
    names: t.List[NameConfig]
    geometry: t.Optional[GeometryConfig] = None
    lookups: t.List[str] = Field(default_factory=list)
    attributes: t.List[AttributeConfig] = Field(default_factory=list)

    model_config = {"populate_by_name": True}

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Feature 'type' must not be empty")
        return value

    @field_validator("names")
    @classmethod
    def validate_names(cls, value: t.List[NameConfig]) -> t.List[NameConfig]:
        if not value:
            raise ValueError("A feature must define at least one name")
        return value

    @model_validator(mode="after")
    def validate_feature(self) -> "FeatureConfig":
        duplicates = {
            lookup for lookup in self.lookups if self.lookups.count(lookup) > 1
        }
        if duplicates:
            raise ValueError(
                f"Feature '{self.type}' lists duplicate lookups: "
                f"{', '.join(sorted(duplicates))}"
            )
        attribute_names = [attribute.name for attribute in self.attributes]
        duplicates = {
            name for name in attribute_names if attribute_names.count(name) > 1
        }
        if duplicates:
            raise ValueError(
                f"Feature '{self.type}' has duplicate attribute names: "
                f"{', '.join(sorted(duplicates))}"
            )
        return self


class GazetteerConfig(BaseModel):
    """Top-level gazetteer configuration."""

    name: str
    crs: str = DEFAULT_CRS
    inputs: t.List[InputConfig]
    lookups: t.Dict[str, LookupConfig] = Field(default_factory=dict)
    features: t.List[FeatureConfig]

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not _NAME_PATTERN.match(value):
            raise ValueError(
                f"Gazetteer name '{value}' must contain only letters, digits, "
                "underscores and hyphens"
            )
        return value

    @field_validator("inputs")
    @classmethod
    def validate_inputs(cls, value: t.List[InputConfig]) -> t.List[InputConfig]:
        if not value:
            raise ValueError("A gazetteer must define at least one input")
        names = [input_config.name for input_config in value]
        duplicates = {name for name in names if names.count(name) > 1}
        if duplicates:
            raise ValueError(
                f"Duplicate input names: {', '.join(sorted(duplicates))}"
            )
        return value

    @field_validator("features")
    @classmethod
    def validate_features(cls, value: t.List[FeatureConfig]) -> t.List[FeatureConfig]:
        if not value:
            raise ValueError("A gazetteer must define at least one feature block")
        return value

    @field_validator("lookups")
    @classmethod
    def validate_lookup_names(
        cls, value: t.Dict[str, LookupConfig]
    ) -> t.Dict[str, LookupConfig]:
        for lookup_name in value:
            if not _IDENTIFIER_PATTERN.match(lookup_name):
                raise ValueError(
                    f"Lookup name '{lookup_name}' must start with a letter or "
                    "underscore and contain only letters, digits and underscores"
                )
        return value

    @model_validator(mode="after")
    def validate_references(self) -> "GazetteerConfig":
        input_names = {input_config.name for input_config in self.inputs}

        for lookup_name, lookup in self.lookups.items():
            if lookup.from_ not in input_names:
                raise ValueError(
                    f"Lookup '{lookup_name}' references unknown input '{lookup.from_}'"
                )

        for feature in self.features:
            if feature.from_ not in input_names:
                raise ValueError(
                    f"Feature '{feature.type}' references unknown input "
                    f"'{feature.from_}'"
                )
            for lookup_name in feature.lookups:
                if lookup_name not in self.lookups:
                    raise ValueError(
                        f"Feature '{feature.type}' references unknown lookup "
                        f"'{lookup_name}'"
                    )
            for name in feature.names:
                if name.from_ is not None and name.from_ not in input_names:
                    raise ValueError(
                        f"Feature '{feature.type}' has a name referencing unknown "
                        f"input '{name.from_}'"
                    )
            # Lookup outputs feed the feature's names, attributes and later
            # lookups; a value name exposed twice would be ambiguous.
            seen_values: t.Dict[str, str] = {}
            for lookup_name in feature.lookups:
                for value_name in self.lookups[lookup_name].values:
                    if value_name in seen_values:
                        raise ValueError(
                            f"Feature '{feature.type}': lookups "
                            f"'{seen_values[value_name]}' and '{lookup_name}' both "
                            f"expose a value named '{value_name}'"
                        )
                    seen_values[value_name] = lookup_name

        return self

    @classmethod
    def from_yaml(cls, path: t.Union[str, Path]) -> "GazetteerConfig":
        """
        Load and validate a gazetteer configuration from a YAML file.

        Relative input paths are resolved against the config file's directory.

        Args:
            path: Path to the YAML configuration file

        Returns:
            Validated GazetteerConfig instance
        """
        with open(path, "r", encoding="utf-8") as config_file:
            data = yaml.safe_load(config_file)
        config = cls.model_validate(data)
        base_dir = Path(path).resolve().parent
        for input_config in config.inputs:
            if input_config.path and not Path(input_config.path).is_absolute():
                input_config.path = str(base_dir / input_config.path)
        return config
