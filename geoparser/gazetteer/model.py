import typing as t
from enum import Enum
from pathlib import Path

import yaml
from pydantic import BaseModel, field_validator, model_validator


class SourceType(str, Enum):
    """Type of source data."""

    TABULAR = "tabular"
    SPATIAL = "spatial"


class DataType(str, Enum):
    """Data type for columns."""

    TEXT = "TEXT"
    INTEGER = "INTEGER"
    REAL = "REAL"
    BLOB = "BLOB"
    GEOMETRY = "GEOMETRY"


class OriginalAttributeConfig(BaseModel):
    """Configuration for an original attribute from source data."""

    name: str
    type: DataType
    index: bool = False
    drop: bool = False
    srid: t.Optional[int] = None

    @model_validator(mode="after")
    def validate_geometry_srid(self) -> "OriginalAttributeConfig":
        """Validate that geometry columns have SRID specified."""
        if self.type == DataType.GEOMETRY and self.srid is None:
            raise ValueError("Geometry columns must specify an SRID")
        if self.type != DataType.GEOMETRY and self.srid is not None:
            raise ValueError("SRID can only be specified for geometry columns")
        return self


class DerivedAttributeConfig(BaseModel):
    """Configuration for a derived attribute computed from expressions."""

    name: str
    type: DataType
    expression: str
    index: bool = False
    srid: t.Optional[int] = None

    @model_validator(mode="after")
    def validate_geometry_srid(self) -> "DerivedAttributeConfig":
        """Validate that geometry columns have SRID specified."""
        if self.type == DataType.GEOMETRY and self.srid is None:
            raise ValueError("Geometry columns must specify an SRID")
        if self.type != DataType.GEOMETRY and self.srid is not None:
            raise ValueError("SRID can only be specified for geometry columns")
        return self


class AttributesConfig(BaseModel):
    """Configuration for original and derived attributes."""

    original: t.List[OriginalAttributeConfig]
    derived: t.List[DerivedAttributeConfig] = []


class SelectConfig(BaseModel):
    """Configuration for a SELECT clause element."""

    source: str  # Source/view name (replaces 'table')
    column: str
    alias: t.Optional[str] = None


class ViewJoinConfig(BaseModel):
    """Configuration for a JOIN clause element in a view."""

    type: str  # e.g., "LEFT JOIN", "INNER JOIN", "RIGHT JOIN"
    source: str  # The source/view to join
    condition: str  # The join condition


class ColumnConfig(BaseModel):
    """Configuration for a column reference."""

    column: str


class NameColumnConfig(BaseModel):
    """Configuration for extracting a name column."""

    column: str
    separator: t.Optional[str] = None


class FeatureConfig(BaseModel):
    """Configuration for extracting features from a source."""

    identifier: t.List[ColumnConfig]  # List of identifier columns
    names: t.List[NameColumnConfig]


class ViewConfig(BaseModel):
    """Configuration for a view over a source."""

    select: t.List[SelectConfig]  # Explicit column selection (required)
    join: t.Optional[t.List[ViewJoinConfig]] = None


class SourceConfig(BaseModel):
    """Configuration for a single source in a gazetteer."""

    name: str
    url: str
    file: str
    type: SourceType
    separator: t.Optional[str] = None
    skiprows: int = 0
    layer: t.Optional[str] = None
    attributes: AttributesConfig
    view: t.Optional[ViewConfig] = None  # Nested view configuration
    features: t.Optional[FeatureConfig] = None  # Nested feature configuration

    @model_validator(mode="after")
    def validate_type_specific_fields(self) -> "SourceConfig":
        """Validate that fields are appropriate for the source type."""
        if self.type == SourceType.TABULAR:
            # Tabular sources must have separator
            if self.separator is None:
                raise ValueError("Tabular sources must specify a separator")
            # Tabular sources should not have layer
            if self.layer is not None:
                raise ValueError("Layer can not be specified for tabular sources")
        elif self.type == SourceType.SPATIAL:
            # Spatial sources should not have separator or skiprows
            if self.separator is not None:
                raise ValueError("Separator can not be specified for spatial sources")
            if self.skiprows != 0:
                raise ValueError("Skiprows can not be specified for spatial sources")

            # For spatial sources, must have exactly one geometry column
            geometry_columns = [
                attr
                for attr in self.attributes.original
                if attr.type == DataType.GEOMETRY
            ]
            geometry_derivations = [
                attr
                for attr in self.attributes.derived
                if attr.type == DataType.GEOMETRY
            ]
            if len(geometry_columns) + len(geometry_derivations) != 1:
                raise ValueError(
                    "Spatial sources must have exactly one geometry column"
                )

        return self

    @model_validator(mode="after")
    def validate_geometry_columns(self) -> "SourceConfig":
        """Validate that there is at most one geometry column named 'geometry'."""
        # Collect all geometry columns from original and derived attributes
        geometry_columns = []

        # Check original attributes
        for attr in self.attributes.original:
            if attr.type == DataType.GEOMETRY:
                geometry_columns.append(("original", attr.name))

        # Check derived attributes
        for attr in self.attributes.derived:
            if attr.type == DataType.GEOMETRY:
                geometry_columns.append(("derived", attr.name))

        # Check that there's at most one geometry column
        if len(geometry_columns) > 1:
            raise ValueError("Sources can have at most one geometry column")

        # Check that any geometry column is named "geometry"
        if geometry_columns and geometry_columns[0][1] != "geometry":
            raise ValueError("The geometry column must be named 'geometry'")

        return self


class GazetteerConfig(BaseModel):
    """Configuration for a gazetteer."""

    name: str
    sources: t.List[SourceConfig]

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate that name contains only allowed characters."""
        if not all(c.isalnum() or c == "_" for c in v):
            raise ValueError(
                "Gazetteer name must contain only alphanumeric characters and underscores"
            )
        return v

    @model_validator(mode="after")
    def validate_unique_source_names(self) -> "GazetteerConfig":
        """Validate that source names are unique within the gazetteer."""
        source_names = [source.name for source in self.sources]
        if len(source_names) != len(set(source_names)):
            raise ValueError("Source names must be unique within a gazetteer")
        return self

    @model_validator(mode="after")
    def validate_view_references(self) -> "GazetteerConfig":
        """Validate that views reference existing sources."""
        source_names = {source.name for source in self.sources}

        # Check that view references are valid
        for source in self.sources:
            if source.view is None:
                continue

            view_config = source.view

            # Check all select source references
            for select_item in view_config.select:
                if select_item.source not in source_names:
                    raise ValueError(
                        f"View for source '{source.name}' select references non-existent source: {select_item.source}"
                    )

            # Check all join source references
            if view_config.join:
                for join_item in view_config.join:
                    if join_item.source not in source_names:
                        raise ValueError(
                            f"View for source '{source.name}' join references non-existent source: {join_item.source}"
                        )

        return self

    @classmethod
    def from_yaml(cls, path: t.Union[str, Path]) -> "GazetteerConfig":
        """
        Load a gazetteer configuration from a YAML file.

        Args:
            path: Path to the YAML configuration file

        Returns:
            GazetteerConfig: Validated gazetteer configuration
        """
        with open(path, "r") as f:
            config_dict = yaml.safe_load(f)

        return cls.model_validate(config_dict)
