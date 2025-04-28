import typing as t
from enum import Enum
from pathlib import Path

import yaml
from pydantic import BaseModel, field_validator, model_validator


class SourceType(str, Enum):
    """Type of source data."""

    TABULAR = "tabular"
    SPATIAL = "spatial"


class ColumnConfig(BaseModel):
    """Configuration for a column in a source file."""

    name: str
    type: str
    keep: bool = True


class GeometryConfig(BaseModel):
    """Configuration for creating geometry from tabular data."""

    x: str
    y: str
    crs: str


class SourceConfig(BaseModel):
    """Configuration for a single source in a gazetteer."""

    id: str
    type: SourceType
    url: str
    file: str
    separator: t.Optional[str] = None
    skiprows: t.Optional[int] = None
    layer: t.Optional[str] = None
    columns: list[ColumnConfig]
    geometry: t.Optional[GeometryConfig] = None

    @model_validator(mode="after")
    def validate_type_specific_fields(self) -> "SourceConfig":
        """Validate that fields are appropriate for the source type."""
        if self.type == SourceType.TABULAR:
            # Tabular sources must have separator and skiprows
            if self.separator is None:
                raise ValueError("Tabular sources must specify a separator")
            if self.skiprows is None:
                raise ValueError("Tabular sources must specify skiprows")
            # Tabular sources should not have layer
            if self.layer is not None:
                raise ValueError("Layer can not be specified for tabular sources")
        elif self.type == SourceType.SPATIAL:
            # Spatial sources should not have separator or skiprows
            if self.separator is not None:
                raise ValueError("Separator can not be specified for spatial sources")
            if self.skiprows is not None:
                raise ValueError("Skiprows can not be specified for spatial sources")
            # Geometry should only be for tabular sources
            if self.geometry is not None:
                raise ValueError("Geometry can not be specified for spatial sources")

        return self


class GazetteerConfig(BaseModel):
    """Configuration for a gazetteer."""

    name: str
    sources: list[SourceConfig]

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
    def validate_unique_source_ids(self) -> "GazetteerConfig":
        """Validate that source IDs are unique within the gazetteer."""
        source_ids = [source.id for source in self.sources]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("Source IDs must be unique within a gazetteer")
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
