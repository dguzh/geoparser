import typing as t
from enum import Enum
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator


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


class AttributeConfig(BaseModel):
    """Configuration for an attribute in a source file."""

    name: str
    type: DataType
    index: bool = False
    primary: bool = False
    drop: bool = False

    @model_validator(mode="after")
    def validate_primary_and_drop(self) -> "AttributeConfig":
        """Validate that a primary attribute cannot be dropped."""
        if self.primary and self.drop:
            raise ValueError("A primary key attribute cannot be dropped")
        return self


class DerivationConfig(BaseModel):
    """Configuration for a derived attribute in a source."""

    name: str
    type: DataType
    index: bool = False
    expression: str


class StatementConfig(BaseModel):
    """SQL statement configuration for a view."""

    select: t.List[str]
    from_: t.List[str] = Field(alias="from")
    join: t.Optional[t.List[str]] = None


class SourceConfig(BaseModel):
    """Configuration for a single source in a gazetteer."""

    name: str
    type: SourceType
    url: str
    file: str
    separator: t.Optional[str] = None
    skiprows: int = 0
    layer: t.Optional[str] = None
    attributes: t.List[AttributeConfig]
    derivations: t.List[DerivationConfig] = []

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
            if self.attributes and self.attributes[-1].name.lower() != "geometry":
                raise ValueError(
                    "For spatial sources, the last attribute must be named 'geometry'"
                )

        return self


class ViewConfig(BaseModel):
    """Configuration for a view over source tables."""

    name: str
    statement: StatementConfig


class FeatureConfig(BaseModel):
    """Configuration for extracting features from a gazetteer source."""

    table: str
    identifier_column: str


class GazetteerConfig(BaseModel):
    """Configuration for a gazetteer."""

    name: str
    sources: t.List[SourceConfig]
    views: t.Optional[t.List[ViewConfig]] = []
    features: t.Optional[t.List[FeatureConfig]] = []

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
        if not self.views:
            return self

        source_names = {source.name for source in self.sources}
        view_names = {view.name for view in self.views}

        # Check for duplicate view names
        if len(view_names) != len(self.views):
            raise ValueError("View names must be unique within a gazetteer")

        # Check for view names that conflict with source names
        conflicts = view_names.intersection(source_names)
        if conflicts:
            raise ValueError(f"View names conflict with source names: {conflicts}")

        # Check that 'from' references existing sources or views
        all_names = source_names.union(view_names)
        for view in self.views:
            for source_ref in view.statement.from_:
                if source_ref not in all_names:
                    raise ValueError(
                        f"View '{view.name}' references non-existent source/view: {source_ref}"
                    )

        return self

    @model_validator(mode="after")
    def validate_feature_references(self) -> "GazetteerConfig":
        """Validate that features reference existing sources or views."""
        if not self.features:
            return self

        source_names = {source.name for source in self.sources}
        view_names = {view.name for view in self.views} if self.views else set()
        all_names = source_names.union(view_names)

        for feature in self.features:
            if feature.table not in all_names:
                raise ValueError(
                    f"Feature configuration references non-existent source/view: {feature.table}"
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
