import typing as t
from enum import Enum
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator


class SourceKind(str, Enum):
    """Kind of source data."""

    TABULAR = "tabular"
    SPATIAL = "spatial"


class DataType(str, Enum):
    """Data type for columns."""

    TEXT = "text"
    INTEGER = "integer"
    REAL = "real"
    BLOB = "blob"
    GEOMETRY = "geometry"


class JoinConditionType(str, Enum):
    """Kind of join condition, used to discriminate between condition shapes."""

    ATTRIBUTE = "attribute"
    SPATIAL = "spatial"


class AttributePredicate(str, Enum):
    """Predicate relating the two sides of an attribute join condition."""

    EQUALS = "equals"


class SpatialPredicate(str, Enum):
    """Predicate relating the two geometries of a spatial join condition."""

    WITHIN = "within"
    INTERSECTS = "intersects"
    CONTAINS = "contains"


class GeometryTransform(str, Enum):
    """Transform applied to a geometry before evaluating a spatial predicate."""

    CENTROID = "centroid"


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


class ColumnConfig(BaseModel):
    """
    Reference to a column in a specific source.

    Written in configuration as the string ``source.column`` and parsed into
    its ``source`` and ``column`` parts. Used wherever a config needs to point
    at a specific column in a specific source (e.g. ``select`` items and join
    operands).
    """

    source: str
    column: str

    @model_validator(mode="before")
    @classmethod
    def parse_reference(cls, data: t.Any) -> t.Any:
        """Allow a ``'source.column'`` string in place of an explicit mapping."""
        if isinstance(data, str):
            parts = data.split(".")
            if len(parts) != 2 or not all(parts):
                raise ValueError(
                    f"Column reference '{data}' must be in the format "
                    "'source.column'"
                )
            return {"source": parts[0], "column": parts[1]}
        return data

    @property
    def sql(self) -> str:
        """The column reference rendered as ``source.column``."""
        return f"{self.source}.{self.column}"


class SelectConfig(BaseModel):
    """Configuration for a SELECT clause element."""

    column: ColumnConfig
    alias: t.Optional[str] = None


class JoinOperandConfig(BaseModel):
    """
    One side (left or right) of a join condition.

    References a column and, for spatial joins, may apply a geometry transform
    (e.g. ``centroid``) before the predicate is evaluated.
    """

    column: ColumnConfig
    transform: t.Optional[GeometryTransform] = None


class ConditionConfig(BaseModel):
    """
    Base configuration for a join condition.

    A condition relates a ``left`` and ``right`` operand, each referencing a
    column. The concrete ``type`` (attribute or spatial) determines how the
    condition is evaluated.
    """

    type: JoinConditionType
    left: JoinOperandConfig
    right: JoinOperandConfig

    @property
    def is_spatial(self) -> bool:
        """Whether this condition is a spatial join."""
        return self.type == JoinConditionType.SPATIAL

    @property
    def left_source(self) -> str:
        """Source/table name of the left operand."""
        return self.left.column.source

    @property
    def left_column(self) -> str:
        """Column name of the left operand."""
        return self.left.column.column

    @property
    def right_source(self) -> str:
        """Source/table name of the right operand."""
        return self.right.column.source

    @property
    def right_column(self) -> str:
        """Column name of the right operand."""
        return self.right.column.column


class AttributeConditionConfig(ConditionConfig):
    """
    Attribute join condition.

    Relates two columns through a non-spatial predicate, producing a plain SQL
    join (e.g. ``left = right`` for the ``equals`` predicate).
    """

    type: t.Literal[JoinConditionType.ATTRIBUTE] = JoinConditionType.ATTRIBUTE
    predicate: AttributePredicate = AttributePredicate.EQUALS

    @model_validator(mode="after")
    def validate_no_transforms(self) -> "AttributeConditionConfig":
        """Validate that attribute operands do not use geometry transforms."""
        if self.left.transform is not None or self.right.transform is not None:
            raise ValueError(
                "Attribute join conditions can not use geometry transforms"
            )
        return self


class SpatialConditionConfig(ConditionConfig):
    """
    Spatial join condition.

    Relates two geometry columns through a spatial predicate (e.g. ``within``).
    Spatial joins are precomputed at install time using GeoPandas, so no spatial
    database extension is required. A geometry operand may optionally be
    transformed (e.g. to its ``centroid``) before the predicate is evaluated.
    """

    type: t.Literal[JoinConditionType.SPATIAL] = JoinConditionType.SPATIAL
    predicate: SpatialPredicate = SpatialPredicate.WITHIN


# Join condition discriminated on the ``type`` field.
JoinConditionConfig = t.Annotated[
    t.Union[AttributeConditionConfig, SpatialConditionConfig],
    Field(discriminator="type"),
]


class ViewJoinConfig(BaseModel):
    """Configuration for a JOIN clause element in a view."""

    method: str  # e.g., "left join", "inner join", "right join"
    condition: JoinConditionConfig  # The join condition

    @property
    def source(self) -> str:
        """Source/table introduced by this join (the right operand's source)."""
        return self.condition.right.column.source


class IdentifierColumnConfig(BaseModel):
    """A column of the source's own table used for feature extraction."""

    column: ColumnConfig


class NameColumnConfig(IdentifierColumnConfig):
    """
    A feature column extracted as a name.

    Optionally provides a ``separator`` used to split a single field into
    multiple names (analogous to how :class:`JoinOperandConfig` wraps a column
    and an optional transform).
    """

    separator: t.Optional[str] = None


class FeatureConfig(BaseModel):
    """
    Configuration for extracting features from a source.

    Features are extracted from the source's own table, so the referenced
    columns all belong to that source.
    """

    identifier: t.List[IdentifierColumnConfig]  # List of identifier columns
    names: t.List[NameColumnConfig]


class ViewConfig(BaseModel):
    """Configuration for a view over a source."""

    select: t.List[SelectConfig]  # Explicit column selection (required)
    join: t.Optional[t.List[ViewJoinConfig]] = None


class SourceConfig(BaseModel):
    """Configuration for a single source in a gazetteer."""

    name: str
    url: t.Optional[str] = None
    path: t.Optional[str] = None
    file: str
    kind: SourceKind
    separator: t.Optional[str] = None
    skiprows: int = 0
    attributes: AttributesConfig
    view: t.Optional[ViewConfig] = None  # Nested view configuration
    features: t.Optional[FeatureConfig] = None  # Nested feature configuration

    @model_validator(mode="after")
    def validate_source_location(self) -> "SourceConfig":
        """Validate that exactly one of url or path is specified."""
        if (self.url is None) == (self.path is None):
            raise ValueError("Must specify exactly one of 'url' or 'path'")
        return self

    @model_validator(mode="after")
    def validate_kind_specific_fields(self) -> "SourceConfig":
        """Validate that fields are appropriate for the source kind."""
        if self.kind == SourceKind.TABULAR:
            # Tabular sources must have separator
            if self.separator is None:
                raise ValueError("Tabular sources must specify a separator")
        elif self.kind == SourceKind.SPATIAL:
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

    @model_validator(mode="after")
    def validate_feature_references(self) -> "SourceConfig":
        """Validate that feature columns reference the source's own table."""
        if self.features is None:
            return self

        feature_columns = [
            item.column for item in self.features.identifier
        ] + [name.column for name in self.features.names]
        for column in feature_columns:
            if column.source != self.name:
                raise ValueError(
                    f"Feature columns must reference the source's own table "
                    f"'{self.name}', got '{column.sql}'"
                )

        return self


class GazetteerConfig(BaseModel):
    """Configuration for a gazetteer."""

    name: str
    sources: t.List[SourceConfig]

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate that name contains only allowed characters."""
        if not all(c.isalnum() or c in "_-" for c in v):
            raise ValueError(
                "Gazetteer name must contain only alphanumeric characters, "
                "underscores, and hyphens"
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
                if select_item.column.source not in source_names:
                    raise ValueError(
                        f"View for source '{source.name}' select references non-existent source: {select_item.column.source}"
                    )

            # Check all join operand source references
            if view_config.join:
                for join_item in view_config.join:
                    for ref_source in (
                        join_item.condition.left_source,
                        join_item.condition.right_source,
                    ):
                        if ref_source not in source_names:
                            raise ValueError(
                                f"View for source '{source.name}' join condition "
                                f"references non-existent source: {ref_source}"
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
