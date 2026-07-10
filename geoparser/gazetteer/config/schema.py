"""
Declarative gazetteer configuration schema.

A gazetteer config describes how source files are projected into the canonical
feature store. It has two top-level concepts:

- ``sources``: files to acquire and stage (transient; discarded after the
  build). Every source declares its ``attributes`` (name and data type), so its
  schema is explicit regardless of file format.
- ``features``: one block per source, describing how that source's rows project
  into canonical features (identifier, names, geometry, data). A block may
  ``join`` other sources to enrich its rows. A feature's ``source`` in the
  artifact is the name of the source it is built from.

Values (``identifier``, ``names``, ``geometry`` and each ``data`` attribute)
are column references or scalar SQL expressions evaluated over the block's
source, aliased ``src``; a bare column name refers to that source, and columns
of joined sources are referenced by qualification (``<source>.<column>``).

Joins are written as raw SQL join clauses (e.g.
``"LEFT JOIN countryInfo ON src.country_code = countryInfo.ISO"``); the whole
joined table is available, and the values to keep are selected in ``data``.
"""

from __future__ import annotations

import re
import typing as t
from enum import Enum
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

# Source names are used as identifiers (staging table names, join aliases), so
# they are restricted to a safe character set.
_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")
_IDENTIFIER_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

DEFAULT_CRS = "EPSG:4326"

# Staged spatial sources always expose their geometry under this attribute name.
GEOMETRY_ATTRIBUTE = "geometry"


class DataType(str, Enum):
    """Data types a source attribute can declare."""

    TEXT = "text"
    INTEGER = "integer"
    REAL = "real"
    GEOMETRY = "geometry"


class AttributeDef(BaseModel):
    """
    A declared attribute (column) of a source.

    The data type is always required, so a source's schema reads the same
    whatever the file format. Spatial sources declare their geometry as an
    attribute of type ``geometry`` named ``geometry``.
    """

    name: str
    type: DataType


class SourceConfig(BaseModel):
    """
    A source file to acquire and stage.

    A source is tabular (delimited text) when ``delimiter`` is set, otherwise
    it is a spatial file readable by DuckDB's spatial extension (shapefile,
    GeoPackage, GeoJSON, ...). Every source declares its ``attributes``; a
    spatial source must declare exactly one geometry attribute (named
    ``geometry``), and a tabular source must declare none.
    """

    name: str
    url: t.Optional[str] = None
    path: t.Optional[str] = None
    file: str

    # Tabular options
    delimiter: t.Optional[str] = None
    quote: t.Optional[str] = None
    skip_rows: int = 0

    # Coordinate reference system of the source's geometry/coordinates
    crs: t.Optional[str] = None

    attributes: t.List[AttributeDef]

    @property
    def is_tabular(self) -> bool:
        """Whether this source is a delimited text file."""
        return self.delimiter is not None

    @property
    def data_attributes(self) -> t.List[AttributeDef]:
        """The non-geometry attributes of this source."""
        return [a for a in self.attributes if a.type != DataType.GEOMETRY]

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not _IDENTIFIER_PATTERN.match(value):
            raise ValueError(
                f"Source name '{value}' must start with a letter or underscore "
                "and contain only letters, digits and underscores"
            )
        return value

    @model_validator(mode="after")
    def validate_source(self) -> "SourceConfig":
        if bool(self.url) == bool(self.path):
            raise ValueError(
                f"Source '{self.name}' must define exactly one of 'url' or 'path'"
            )

        if not self.attributes:
            raise ValueError(
                f"Source '{self.name}' must declare at least one attribute"
            )
        names = [attribute.name for attribute in self.attributes]
        duplicates = {name for name in names if names.count(name) > 1}
        if duplicates:
            raise ValueError(
                f"Source '{self.name}' has duplicate attribute names: "
                f"{', '.join(sorted(duplicates))}"
            )

        geometry_attributes = [
            a for a in self.attributes if a.type == DataType.GEOMETRY
        ]
        if self.is_tabular:
            if geometry_attributes:
                raise ValueError(
                    f"Source '{self.name}': tabular sources cannot declare a "
                    "geometry attribute"
                )
        else:
            for field in ("quote",):
                if getattr(self, field) is not None:
                    raise ValueError(
                        f"Source '{self.name}': '{field}' is only valid for tabular "
                        "sources (those with a 'delimiter')"
                    )
            if self.skip_rows:
                raise ValueError(
                    f"Source '{self.name}': 'skip_rows' is only valid for tabular "
                    "sources"
                )
            if len(geometry_attributes) != 1:
                raise ValueError(
                    f"Source '{self.name}': a spatial source must declare exactly "
                    "one geometry attribute"
                )
            if geometry_attributes[0].name != GEOMETRY_ATTRIBUTE:
                raise ValueError(
                    f"Source '{self.name}': the geometry attribute must be named "
                    f"'{GEOMETRY_ATTRIBUTE}'"
                )
        return self


class DataConfig(BaseModel):
    """
    A value stored in the feature's JSON data object.

    ``attribute`` is a column of the block's source (bare), a column of a joined
    source (qualified as ``<source>.<column>``) or a scalar SQL expression;
    ``alias`` is the key it is stored under. When ``alias`` is omitted,
    ``attribute`` must be a bare column of the block's source and is used as the
    key. The string shorthand ``"name"`` is equivalent to ``{attribute: name}``.
    """

    attribute: str
    alias: t.Optional[str] = None

    @property
    def output_name(self) -> str:
        """The key the value is stored under."""
        return self.alias or self.attribute

    @model_validator(mode="before")
    @classmethod
    def coerce_shorthand(cls, value: t.Any) -> t.Any:
        if isinstance(value, str):
            return {"attribute": value}
        return value

    @model_validator(mode="after")
    def validate_data(self) -> "DataConfig":
        if self.alias is None and not _IDENTIFIER_PATTERN.match(self.attribute):
            raise ValueError(
                f"Data value '{self.attribute}' is a qualified reference or "
                "expression, so it needs an 'alias' to name the stored key"
            )
        return self


class FeatureConfig(BaseModel):
    """
    Projection of one source into canonical features.

    Rows of ``source`` (enriched by ``joins``) are grouped by ``identifier``;
    each group becomes one feature with the listed names, geometry and data.
    Rows sharing an identifier are merged by collecting all names, unioning
    their geometries and keeping the first row's data values. The feature's
    ``source`` in the artifact is the name of ``source``.

    ``joins`` are raw SQL join clauses appended to ``FROM <source> AS src``, so
    they may reference the block's source as ``src`` and any joined (or earlier
    joined) source by name; the whole joined table is available and the values
    to keep are selected in ``data``.
    """

    source: str
    joins: t.List[str] = Field(default_factory=list)
    identifier: str
    geometry: t.Optional[str] = None
    names: t.List[str]
    data: t.List[DataConfig] = Field(default_factory=list)

    @field_validator("names")
    @classmethod
    def validate_names(cls, value: t.List[str]) -> t.List[str]:
        if not value:
            raise ValueError("A feature must define at least one name")
        for name in value:
            if not isinstance(name, str) or not name.strip():
                raise ValueError("A feature name must be a non-empty string")
        return value

    @field_validator("joins")
    @classmethod
    def validate_joins(cls, value: t.List[str]) -> t.List[str]:
        for join in value:
            if not isinstance(join, str) or not join.strip():
                raise ValueError("A join must be a non-empty SQL join clause")
        return value

    @model_validator(mode="after")
    def validate_feature(self) -> "FeatureConfig":
        data_names = [item.output_name for item in self.data]
        duplicates = {name for name in data_names if data_names.count(name) > 1}
        if duplicates:
            raise ValueError(
                f"Feature '{self.source}' has duplicate data keys: "
                f"{', '.join(sorted(duplicates))}"
            )
        return self


class GazetteerConfig(BaseModel):
    """Top-level gazetteer configuration."""

    name: str
    crs: str = DEFAULT_CRS
    sources: t.List[SourceConfig]
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

    @field_validator("sources")
    @classmethod
    def validate_sources(cls, value: t.List[SourceConfig]) -> t.List[SourceConfig]:
        if not value:
            raise ValueError("A gazetteer must define at least one source")
        names = [source.name for source in value]
        duplicates = {name for name in names if names.count(name) > 1}
        if duplicates:
            raise ValueError(f"Duplicate source names: {', '.join(sorted(duplicates))}")
        return value

    @field_validator("features")
    @classmethod
    def validate_features(cls, value: t.List[FeatureConfig]) -> t.List[FeatureConfig]:
        if not value:
            raise ValueError("A gazetteer must define at least one feature block")
        sources = [feature.source for feature in value]
        duplicates = {name for name in sources if sources.count(name) > 1}
        if duplicates:
            raise ValueError(
                "Each source can back at most one feature block, but these back "
                f"several: {', '.join(sorted(duplicates))}"
            )
        return value

    @model_validator(mode="after")
    def validate_references(self) -> "GazetteerConfig":
        source_names = {source.name for source in self.sources}

        for feature in self.features:
            if feature.source not in source_names:
                raise ValueError(
                    f"Feature references unknown source '{feature.source}'"
                )
        return self

    @classmethod
    def from_yaml(cls, path: t.Union[str, Path]) -> "GazetteerConfig":
        """
        Load and validate a gazetteer configuration from a YAML file.

        Relative source paths are resolved against the config file's directory.

        Args:
            path: Path to the YAML configuration file

        Returns:
            Validated GazetteerConfig instance
        """
        with open(path, "r", encoding="utf-8") as config_file:
            data = yaml.safe_load(config_file)
        config = cls.model_validate(data)
        base_dir = Path(path).resolve().parent
        for source in config.sources:
            if source.path and not Path(source.path).is_absolute():
                source.path = str(base_dir / source.path)
        return config
