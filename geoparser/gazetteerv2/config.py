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


class SourceColumnConfig(BaseModel):
    """Configuration for a column in a source file."""

    name: str
    type: DataType
    primary: bool = False
    drop: bool = False

    @model_validator(mode="after")
    def validate_primary_and_drop(self) -> "SourceColumnConfig":
        """Validate that a primary column cannot be dropped."""
        if self.primary and self.drop:
            raise ValueError("A primary key column cannot be dropped")
        return self


class DerivedColumnConfig(BaseModel):
    """Configuration for a derived column created from an expression."""

    name: str
    type: DataType
    expression: str


class RelationshipConfig(BaseModel):
    """Configuration for a relationship between two sources."""

    local: str
    remote: str

    @property
    def local_table(self) -> str:
        """Get the local table name from the relationship definition."""
        return self.local.split(".")[0]

    @property
    def local_column(self) -> str:
        """Get the local column name from the relationship definition."""
        return self.local.split(".")[1]

    @property
    def remote_table(self) -> str:
        """Get the remote table name from the relationship definition."""
        return self.remote.split(".")[0]

    @property
    def remote_column(self) -> str:
        """Get the remote column name from the relationship definition."""
        return self.remote.split(".")[1]


class SourceConfig(BaseModel):
    """Configuration for a single source in a gazetteer."""

    name: str
    type: SourceType
    url: str
    file: str
    separator: t.Optional[str] = None
    skiprows: int = 0
    layer: t.Optional[str] = None
    source_columns: list[SourceColumnConfig]
    derived_columns: list[DerivedColumnConfig] = []

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

            # For spatial sources, check if the last column is named "geometry"
            if (
                self.source_columns
                and self.source_columns[-1].name.lower() != "geometry"
            ):
                raise ValueError(
                    "For spatial sources, the last source_column must be named 'geometry'"
                )

        return self


class GazetteerConfig(BaseModel):
    """Configuration for a gazetteer."""

    name: str
    sources: list[SourceConfig]
    relationships: list[RelationshipConfig] = []

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
    def validate_relationships(self) -> "GazetteerConfig":
        """Validate that relationships reference existing sources."""
        source_names = {source.name for source in self.sources}

        for rel in self.relationships:
            if rel.local_table not in source_names:
                raise ValueError(
                    f"Relationship references non-existent source: {rel.local_table}"
                )
            if rel.remote_table not in source_names:
                raise ValueError(
                    f"Relationship references non-existent source: {rel.remote_table}"
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
