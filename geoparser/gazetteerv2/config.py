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
    GEOMETRY = "GEOMETRY"


class AttributeConfig(BaseModel):
    """Configuration for an attribute in a source file."""

    name: str
    type: DataType
    index: bool = False
    drop: bool = False
    srid: t.Optional[int] = None

    @model_validator(mode="after")
    def validate_geometry_srid(self) -> "AttributeConfig":
        """Validate that geometry columns have SRID specified."""
        if self.type == DataType.GEOMETRY and self.srid is None:
            raise ValueError("Geometry columns must specify an SRID")
        if self.type != DataType.GEOMETRY and self.srid is not None:
            raise ValueError("SRID can only be specified for geometry columns")
        return self


class DerivationConfig(BaseModel):
    """Configuration for a derived attribute in a source."""

    name: str
    type: DataType
    index: bool = False
    expression: str
    srid: t.Optional[int] = None

    @model_validator(mode="after")
    def validate_geometry_srid(self) -> "DerivationConfig":
        """Validate that geometry derivations have SRID specified."""
        if self.type == DataType.GEOMETRY and self.srid is None:
            raise ValueError("Geometry derivations must specify an SRID")
        if self.type != DataType.GEOMETRY and self.srid is not None:
            raise ValueError("SRID can only be specified for geometry derivations")
        return self


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

            # For spatial sources, must have exactly one geometry column
            geometry_columns = [
                attr for attr in self.attributes if attr.type == DataType.GEOMETRY
            ]
            geometry_derivations = [
                deriv for deriv in self.derivations if deriv.type == DataType.GEOMETRY
            ]
            if len(geometry_columns) + len(geometry_derivations) != 1:
                raise ValueError(
                    "Spatial sources must have exactly one geometry column"
                )

        return self

    @model_validator(mode="after")
    def validate_geometry_columns(self) -> "SourceConfig":
        """Validate that there is at most one geometry column named 'geometry'."""
        # Collect all geometry columns from attributes and derivations
        geometry_columns = []

        # Check attributes
        for attr in self.attributes:
            if attr.type == DataType.GEOMETRY:
                geometry_columns.append(("attribute", attr.name))

        # Check derivations
        for deriv in self.derivations:
            if deriv.type == DataType.GEOMETRY:
                geometry_columns.append(("derivation", deriv.name))

        # Check that there's at most one geometry column
        if len(geometry_columns) > 1:
            raise ValueError("Sources can have at most one geometry column")

        # Check that any geometry column is named "geometry"
        if geometry_columns and geometry_columns[0][1] != "geometry":
            raise ValueError("The geometry column must be named 'geometry'")

        return self


class ViewConfig(BaseModel):
    """Configuration for a view over source tables."""

    name: str
    statement: StatementConfig


class FeatureConfig(BaseModel):
    """Configuration for extracting features from a gazetteer source."""

    table: str
    view: t.Optional[str] = None
    identifier_column: str


class ToponymConfig(BaseModel):
    """Configuration for extracting toponyms from a gazetteer source."""

    table: str
    view: t.Optional[str] = None
    identifier_column: str
    toponym_column: str
    separator: t.Optional[str] = None


class GazetteerConfig(BaseModel):
    """Configuration for a gazetteer."""

    name: str
    sources: t.List[SourceConfig]
    views: t.Optional[t.List[ViewConfig]] = []
    features: t.Optional[t.List[FeatureConfig]] = []
    toponyms: t.Optional[t.List[ToponymConfig]] = []

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
                    f"Feature configuration table references non-existent source/view: {feature.table}"
                )
            if feature.view and feature.view not in all_names:
                raise ValueError(
                    f"Feature configuration view references non-existent source/view: {feature.view}"
                )

        return self

    @model_validator(mode="after")
    def validate_toponym_references(self) -> "GazetteerConfig":
        """Validate that toponyms reference existing sources or views."""
        if not self.toponyms:
            return self

        source_names = {source.name for source in self.sources}
        view_names = {view.name for view in self.views} if self.views else set()
        all_names = source_names.union(view_names)

        for toponym_config in self.toponyms:
            if toponym_config.table not in all_names:
                raise ValueError(
                    f"Toponym configuration table references non-existent source/view: {toponym_config.table}"
                )
            if toponym_config.view and toponym_config.view not in all_names:
                raise ValueError(
                    f"Toponym configuration view references non-existent source/view: {toponym_config.view}"
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
