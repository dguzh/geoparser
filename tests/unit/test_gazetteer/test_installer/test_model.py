"""
Unit tests for geoparser/gazetteer/installer/model.py

Tests configuration models and validators for gazetteer installation.
"""

import tempfile
from pathlib import Path

import pytest
import yaml

from geoparser.gazetteer.installer.model import (
    AttributeConditionConfig,
    AttributePredicate,
    AttributesConfig,
    ColumnConfig,
    DataType,
    DerivedAttributeConfig,
    FeatureConfig,
    GazetteerConfig,
    GeometryTransform,
    IdentifierColumnConfig,
    JoinConditionType,
    JoinOperandConfig,
    NameColumnConfig,
    OriginalAttributeConfig,
    SelectConfig,
    SourceConfig,
    SourceKind,
    SpatialConditionConfig,
    SpatialPredicate,
    ViewConfig,
    ViewJoinConfig,
)


@pytest.mark.unit
class TestDataTypeEnum:
    """Test DataType enum."""

    def test_has_text_type(self):
        """Test that DATA_TYPE has TEXT."""
        assert DataType.TEXT == "text"

    def test_has_integer_type(self):
        """Test that DataType has INTEGER."""
        assert DataType.INTEGER == "integer"

    def test_has_real_type(self):
        """Test that DataType has REAL."""
        assert DataType.REAL == "real"

    def test_has_blob_type(self):
        """Test that DataType has BLOB."""
        assert DataType.BLOB == "blob"

    def test_has_geometry_type(self):
        """Test that DataType has GEOMETRY."""
        assert DataType.GEOMETRY == "geometry"


@pytest.mark.unit
class TestSourceKindEnum:
    """Test SourceKind enum."""

    def test_has_tabular_kind(self):
        """Test that SourceKind has TABULAR."""
        assert SourceKind.TABULAR == "tabular"

    def test_has_spatial_kind(self):
        """Test that SourceKind has SPATIAL."""
        assert SourceKind.SPATIAL == "spatial"


@pytest.mark.unit
class TestOriginalAttributeConfig:
    """Test OriginalAttributeConfig model."""

    def test_creates_with_valid_data(self):
        """Test creating with valid non-geometry data."""
        # Act
        attr = OriginalAttributeConfig(name="test_col", type=DataType.TEXT)

        # Assert
        assert attr.name == "test_col"
        assert attr.type == DataType.TEXT
        assert attr.index is False
        assert attr.drop is False
        assert attr.srid is None

    def test_creates_with_index_flag(self):
        """Test creating with index flag set."""
        # Act
        attr = OriginalAttributeConfig(name="id", type=DataType.INTEGER, index=True)

        # Assert
        assert attr.index is True

    def test_creates_with_drop_flag(self):
        """Test creating with drop flag set."""
        # Act
        attr = OriginalAttributeConfig(name="temp", type=DataType.TEXT, drop=True)

        # Assert
        assert attr.drop is True

    def test_geometry_column_requires_srid(self):
        """Test that geometry columns must have SRID."""
        # Act & Assert
        with pytest.raises(ValueError, match="Geometry columns must specify an SRID"):
            OriginalAttributeConfig(name="geom", type=DataType.GEOMETRY)

    def test_geometry_column_accepts_srid(self):
        """Test that geometry columns can have SRID."""
        # Act
        attr = OriginalAttributeConfig(name="geom", type=DataType.GEOMETRY, srid=4326)

        # Assert
        assert attr.srid == 4326

    def test_non_geometry_column_rejects_srid(self):
        """Test that non-geometry columns cannot have SRID."""
        # Act & Assert
        with pytest.raises(
            ValueError, match="SRID can only be specified for geometry columns"
        ):
            OriginalAttributeConfig(name="text_col", type=DataType.TEXT, srid=4326)


@pytest.mark.unit
class TestDerivedAttributeConfig:
    """Test DerivedAttributeConfig model."""

    def test_creates_with_valid_data(self):
        """Test creating with valid derived attribute."""
        # Act
        attr = DerivedAttributeConfig(
            name="full_name",
            type=DataType.TEXT,
            expression="first_name || ' ' || last_name",
        )

        # Assert
        assert attr.name == "full_name"
        assert attr.type == DataType.TEXT
        assert attr.expression == "first_name || ' ' || last_name"
        assert attr.index is False
        assert attr.srid is None

    def test_geometry_column_requires_srid(self):
        """Test that derived geometry columns must have SRID."""
        # Act & Assert
        with pytest.raises(ValueError, match="Geometry columns must specify an SRID"):
            DerivedAttributeConfig(
                name="geometry",
                type=DataType.GEOMETRY,
                expression="MakePoint(x, y)",
            )

    def test_geometry_column_accepts_srid(self):
        """Test that derived geometry columns can have SRID."""
        # Act
        attr = DerivedAttributeConfig(
            name="geometry",
            type=DataType.GEOMETRY,
            expression="MakePoint(x, y)",
            srid=4326,
        )

        # Assert
        assert attr.srid == 4326

    def test_non_geometry_column_cannot_have_srid(self):
        """Test that non-geometry columns cannot have SRID specified."""
        # Act & Assert
        with pytest.raises(
            ValueError, match="SRID can only be specified for geometry columns"
        ):
            DerivedAttributeConfig(
                name="id",
                type=DataType.INTEGER,
                expression="1",
                srid=4326,
            )


@pytest.mark.unit
class TestAttributesConfig:
    """Test AttributesConfig model."""

    def test_creates_with_original_only(self):
        """Test creating with only original attributes."""
        # Act
        attrs = AttributesConfig(
            original=[
                OriginalAttributeConfig(name="id", type=DataType.INTEGER),
                OriginalAttributeConfig(name="name", type=DataType.TEXT),
            ]
        )

        # Assert
        assert len(attrs.original) == 2
        assert len(attrs.derived) == 0

    def test_creates_with_derived_attributes(self):
        """Test creating with derived attributes."""
        # Act
        attrs = AttributesConfig(
            original=[OriginalAttributeConfig(name="first", type=DataType.TEXT)],
            derived=[
                DerivedAttributeConfig(
                    name="upper_first", type=DataType.TEXT, expression="upper(first)"
                )
            ],
        )

        # Assert
        assert len(attrs.original) == 1
        assert len(attrs.derived) == 1


@pytest.mark.unit
class TestSelectConfig:
    """Test SelectConfig model."""

    def test_creates_with_column_reference(self):
        """Test creating with a 'source.column' reference."""
        # Act
        select = SelectConfig(column="table1.col1")

        # Assert
        assert select.column.source == "table1"
        assert select.column.column == "col1"
        assert select.alias is None

    def test_creates_with_alias(self):
        """Test creating with alias."""
        # Act
        select = SelectConfig(column="table1.col1", alias="renamed_col")

        # Assert
        assert select.alias == "renamed_col"


@pytest.mark.unit
class TestViewJoinConfig:
    """Test ViewJoinConfig model."""

    def test_creates_with_attribute_condition(self):
        """Test creating with an attribute equality condition."""
        # Act
        join = ViewJoinConfig(
            method="left join",
            condition=AttributeConditionConfig(
                predicate="equals",
                left=JoinOperandConfig(column="table1.id"),
                right=JoinOperandConfig(column="table2.ref_id"),
            ),
        )

        # Assert
        assert join.method == "left join"
        assert join.source == "table2"
        assert join.condition.type == JoinConditionType.ATTRIBUTE
        assert join.condition.predicate == AttributePredicate.EQUALS
        assert not join.condition.is_spatial

    def test_creates_with_spatial_condition(self):
        """Test creating a join whose condition is a spatial join."""
        # Act
        join = ViewJoinConfig(
            method="left join",
            condition=SpatialConditionConfig(
                predicate="within",
                left=JoinOperandConfig(column="places.geometry"),
                right=JoinOperandConfig(column="regions.geometry"),
            ),
        )

        # Assert
        assert join.condition.type == JoinConditionType.SPATIAL
        assert join.condition.predicate == SpatialPredicate.WITHIN
        assert join.condition.is_spatial

    def test_parses_attribute_condition_from_mapping(self):
        """Test that a mapping with type 'attribute' parses to the right model."""
        # Act
        join = ViewJoinConfig(
            method="left join",
            condition={
                "type": "attribute",
                "predicate": "equals",
                "left": {"column": "places.admin_code"},
                "right": {"column": "regions.code"},
            },
        )

        # Assert
        assert isinstance(join.condition, AttributeConditionConfig)
        assert join.condition.left_source == "places"

    def test_parses_spatial_condition_from_mapping(self):
        """Test that a mapping with type 'spatial' parses to the right model."""
        # Act
        join = ViewJoinConfig(
            method="left join",
            condition={
                "type": "spatial",
                "predicate": "within",
                "left": {"column": "places.geometry"},
                "right": {"column": "regions.geometry"},
            },
        )

        # Assert
        assert isinstance(join.condition, SpatialConditionConfig)
        assert join.condition.left_source == "places"

    def test_derives_source_from_right_operand(self):
        """Test that the joined source is inferred from the right operand."""
        # Act
        join = ViewJoinConfig(
            method="left join",
            condition=AttributeConditionConfig(
                left=JoinOperandConfig(column="places.admin_code"),
                right=JoinOperandConfig(column="regions.code"),
            ),
        )

        # Assert
        assert join.source == "regions"

    def test_requires_condition(self):
        """Test that a join must specify a condition."""
        # Act & Assert
        with pytest.raises(ValueError):
            ViewJoinConfig(method="left join")


@pytest.mark.unit
class TestAttributeConditionConfig:
    """Test AttributeConditionConfig model."""

    def test_defaults(self):
        """Test that an attribute condition defaults to the equals predicate."""
        # Act
        condition = AttributeConditionConfig(
            left=JoinOperandConfig(column="places.admin_code"),
            right=JoinOperandConfig(column="regions.code"),
        )

        # Assert
        assert condition.type == JoinConditionType.ATTRIBUTE
        assert condition.predicate == AttributePredicate.EQUALS
        assert not condition.is_spatial

    def test_parses_source_and_column_references(self):
        """Test that left/right operands expose source and column parts."""
        # Act
        condition = AttributeConditionConfig(
            left=JoinOperandConfig(column="places.admin_code"),
            right=JoinOperandConfig(column="regions.code"),
        )

        # Assert
        assert condition.left_source == "places"
        assert condition.left_column == "admin_code"
        assert condition.right_source == "regions"
        assert condition.right_column == "code"

    def test_rejects_invalid_reference(self):
        """Test that references must use the 'source.column' format."""
        # Act & Assert
        with pytest.raises(ValueError, match="format 'source.column'"):
            AttributeConditionConfig(
                left={"column": "places"},
                right={"column": "regions.code"},
            )

    def test_rejects_geometry_transform(self):
        """Test that attribute operands can not use a geometry transform."""
        # Act & Assert
        with pytest.raises(ValueError, match="can not use geometry transforms"):
            AttributeConditionConfig(
                left=JoinOperandConfig(
                    column="places.admin_code", transform="centroid"
                ),
                right=JoinOperandConfig(column="regions.code"),
            )


@pytest.mark.unit
class TestSpatialConditionConfig:
    """Test SpatialConditionConfig model."""

    def test_defaults(self):
        """Test that a spatial condition defaults to the within predicate."""
        # Act
        condition = SpatialConditionConfig(
            left=JoinOperandConfig(column="places.geometry"),
            right=JoinOperandConfig(column="regions.geometry"),
        )

        # Assert
        assert condition.type == JoinConditionType.SPATIAL
        assert condition.predicate == SpatialPredicate.WITHIN
        assert condition.is_spatial
        assert condition.left.transform is None
        assert condition.right.transform is None

    def test_parses_source_and_column_references(self):
        """Test that left/right operands expose source and column parts."""
        # Act
        condition = SpatialConditionConfig(
            predicate="within",
            left=JoinOperandConfig(column="places.geom"),
            right=JoinOperandConfig(column="regions.boundary"),
        )

        # Assert
        assert condition.left_source == "places"
        assert condition.left_column == "geom"
        assert condition.right_source == "regions"
        assert condition.right_column == "boundary"

    def test_accepts_centroid_transform(self):
        """Test that a centroid transform can be specified on an operand."""
        # Act
        condition = SpatialConditionConfig(
            predicate="within",
            left=JoinOperandConfig(column="roads.geometry", transform="centroid"),
            right=JoinOperandConfig(column="regions.geometry"),
        )

        # Assert
        assert condition.left.transform == GeometryTransform.CENTROID

    def test_rejects_invalid_reference(self):
        """Test that references must use the 'source.column' format."""
        # Act & Assert
        with pytest.raises(ValueError, match="format 'source.column'"):
            SpatialConditionConfig(
                predicate="within",
                left={"column": "places"},
                right={"column": "regions.geometry"},
            )


@pytest.mark.unit
class TestColumnConfig:
    """Test ColumnConfig model."""

    def test_parses_source_dot_column_string(self):
        """Test that a 'source.column' string is parsed into its parts."""
        # Act
        col = ColumnConfig.model_validate("table1.col1")

        # Assert
        assert col.source == "table1"
        assert col.column == "col1"
        assert col.sql == "table1.col1"

    def test_creates_from_explicit_parts(self):
        """Test creating from explicit source and column."""
        # Act
        col = ColumnConfig(source="table1", column="col1")

        # Assert
        assert col.sql == "table1.col1"

    def test_rejects_invalid_reference(self):
        """Test that a reference must use the 'source.column' format."""
        # Act & Assert
        with pytest.raises(ValueError, match="format 'source.column'"):
            ColumnConfig.model_validate("invalid")


@pytest.mark.unit
class TestNameColumnConfig:
    """Test NameColumnConfig model."""

    def test_creates_without_separator(self):
        """Test creating without separator."""
        # Act
        name_col = NameColumnConfig(column="places.name")

        # Assert
        assert name_col.column.source == "places"
        assert name_col.column.column == "name"
        assert name_col.separator is None

    def test_creates_with_separator(self):
        """Test creating with separator."""
        # Act
        name_col = NameColumnConfig(column="places.names", separator=",")

        # Assert
        assert name_col.separator == ","


@pytest.mark.unit
class TestFeatureConfig:
    """Test FeatureConfig model."""

    def test_creates_with_identifier_and_names(self):
        """Test creating with identifier and names."""
        # Act
        feature = FeatureConfig(
            identifier=[IdentifierColumnConfig(column="places.id")],
            names=[NameColumnConfig(column="places.name")],
        )

        # Assert
        assert len(feature.identifier) == 1
        assert feature.identifier[0].column.source == "places"
        assert len(feature.names) == 1
        assert feature.names[0].column.column == "name"


@pytest.mark.unit
class TestViewConfig:
    """Test ViewConfig model."""

    def test_creates_with_select_only(self):
        """Test creating with select only."""
        # Act
        view = ViewConfig(select=[SelectConfig(column="table1.col1")])

        # Assert
        assert len(view.select) == 1
        assert view.join is None

    def test_creates_with_join(self):
        """Test creating with join."""
        # Act
        view = ViewConfig(
            select=[SelectConfig(column="t1.col1")],
            join=[
                ViewJoinConfig(
                    method="left join",
                    condition=AttributeConditionConfig(
                        left=JoinOperandConfig(column="t1.id"),
                        right=JoinOperandConfig(column="t2.id"),
                    ),
                )
            ],
        )

        # Assert
        assert len(view.join) == 1


@pytest.mark.unit
class TestSourceConfig:
    """Test SourceConfig model."""

    def test_creates_tabular_source_with_url(self):
        """Test creating tabular source with URL."""
        # Act
        source = SourceConfig(
            name="test_source",
            url="http://example.com/data.csv",
            file="data.csv",
            kind=SourceKind.TABULAR,
            separator="\t",
            attributes=AttributesConfig(
                original=[OriginalAttributeConfig(name="id", type=DataType.INTEGER)]
            ),
        )

        # Assert
        assert source.name == "test_source"
        assert source.url == "http://example.com/data.csv"
        assert source.kind == SourceKind.TABULAR
        assert source.separator == "\t"

    def test_creates_tabular_source_with_path(self):
        """Test creating tabular source with local path."""
        # Act
        source = SourceConfig(
            name="test_source",
            path="/local/data.csv",
            file="data.csv",
            kind=SourceKind.TABULAR,
            separator=",",
            attributes=AttributesConfig(
                original=[OriginalAttributeConfig(name="id", type=DataType.INTEGER)]
            ),
        )

        # Assert
        assert source.path == "/local/data.csv"
        assert source.url is None

    def test_rejects_both_url_and_path(self):
        """Test that specifying both URL and path is rejected."""
        # Act & Assert
        with pytest.raises(ValueError, match="Must specify exactly one of"):
            SourceConfig(
                name="test",
                url="http://example.com/data.csv",
                path="/local/data.csv",
                file="data.csv",
                kind=SourceKind.TABULAR,
                separator=",",
                attributes=AttributesConfig(
                    original=[OriginalAttributeConfig(name="id", type=DataType.INTEGER)]
                ),
            )

    def test_rejects_neither_url_nor_path(self):
        """Test that specifying neither URL nor path is rejected."""
        # Act & Assert
        with pytest.raises(ValueError, match="Must specify exactly one of"):
            SourceConfig(
                name="test",
                file="data.csv",
                kind=SourceKind.TABULAR,
                separator=",",
                attributes=AttributesConfig(
                    original=[OriginalAttributeConfig(name="id", type=DataType.INTEGER)]
                ),
            )

    def test_tabular_requires_separator(self):
        """Test that tabular sources must have separator."""
        # Act & Assert
        with pytest.raises(
            ValueError, match="Tabular sources must specify a separator"
        ):
            SourceConfig(
                name="test",
                url="http://example.com/data.csv",
                file="data.csv",
                kind=SourceKind.TABULAR,
                attributes=AttributesConfig(
                    original=[OriginalAttributeConfig(name="id", type=DataType.INTEGER)]
                ),
            )

    def test_spatial_rejects_separator(self):
        """Test that spatial sources cannot have separator."""
        # Act & Assert
        with pytest.raises(
            ValueError, match="Separator can not be specified for spatial sources"
        ):
            SourceConfig(
                name="test",
                url="http://example.com/data.shp",
                file="data.shp",
                kind=SourceKind.SPATIAL,
                separator=",",
                attributes=AttributesConfig(
                    original=[
                        OriginalAttributeConfig(
                            name="geometry", type=DataType.GEOMETRY, srid=4326
                        )
                    ]
                ),
            )

    def test_spatial_rejects_skiprows(self):
        """Test that spatial sources cannot have skiprows."""
        # Act & Assert
        with pytest.raises(
            ValueError, match="Skiprows can not be specified for spatial sources"
        ):
            SourceConfig(
                name="test",
                url="http://example.com/data.shp",
                file="data.shp",
                kind=SourceKind.SPATIAL,
                skiprows=1,
                attributes=AttributesConfig(
                    original=[
                        OriginalAttributeConfig(
                            name="geometry", type=DataType.GEOMETRY, srid=4326
                        )
                    ]
                ),
            )

    def test_spatial_requires_exactly_one_geometry_column(self):
        """Test that spatial sources must have exactly one geometry column."""
        # Act & Assert - No geometry
        with pytest.raises(
            ValueError, match="Spatial sources must have exactly one geometry column"
        ):
            SourceConfig(
                name="test",
                url="http://example.com/data.shp",
                file="data.shp",
                kind=SourceKind.SPATIAL,
                attributes=AttributesConfig(
                    original=[OriginalAttributeConfig(name="id", type=DataType.INTEGER)]
                ),
            )

    def test_spatial_accepts_single_geometry_column(self):
        """Test that spatial sources accept exactly one geometry column."""
        # Act
        source = SourceConfig(
            name="test",
            url="http://example.com/data.shp",
            file="data.shp",
            kind=SourceKind.SPATIAL,
            attributes=AttributesConfig(
                original=[
                    OriginalAttributeConfig(name="id", type=DataType.INTEGER),
                    OriginalAttributeConfig(
                        name="geometry", type=DataType.GEOMETRY, srid=4326
                    ),
                ]
            ),
        )

        # Assert
        assert source.kind == SourceKind.SPATIAL

    def test_rejects_multiple_geometry_columns(self):
        """Test that sources cannot have multiple geometry columns."""
        # Act & Assert
        with pytest.raises(
            ValueError, match="Sources can have at most one geometry column"
        ):
            SourceConfig(
                name="test",
                url="http://example.com/data.csv",
                file="data.csv",
                kind=SourceKind.TABULAR,
                separator=",",
                attributes=AttributesConfig(
                    original=[
                        OriginalAttributeConfig(
                            name="geometry", type=DataType.GEOMETRY, srid=4326
                        ),
                        OriginalAttributeConfig(
                            name="geom2", type=DataType.GEOMETRY, srid=4326
                        ),
                    ]
                ),
            )

    def test_geometry_column_must_be_named_geometry(self):
        """Test that geometry column must be named 'geometry'."""
        # Act & Assert
        with pytest.raises(
            ValueError, match="The geometry column must be named 'geometry'"
        ):
            SourceConfig(
                name="test",
                url="http://example.com/data.shp",
                file="data.shp",
                kind=SourceKind.SPATIAL,
                attributes=AttributesConfig(
                    original=[
                        OriginalAttributeConfig(
                            name="geom", type=DataType.GEOMETRY, srid=4326
                        )
                    ]
                ),
            )

    def test_accepts_feature_columns_from_own_table(self):
        """Test that feature columns referencing the source's own table pass."""
        # Act
        source = SourceConfig(
            name="places",
            url="http://example.com/data.csv",
            file="data.csv",
            kind=SourceKind.TABULAR,
            separator=",",
            attributes=AttributesConfig(
                original=[OriginalAttributeConfig(name="id", type=DataType.INTEGER)]
            ),
            features=FeatureConfig(
                identifier=[IdentifierColumnConfig(column="places.id")],
                names=[NameColumnConfig(column="places.id")],
            ),
        )

        # Assert
        assert source.features.identifier[0].column.source == "places"

    def test_rejects_feature_columns_from_other_table(self):
        """Test that feature columns must reference the source's own table."""
        # Act & Assert
        with pytest.raises(
            ValueError, match="Feature columns must reference the source's own table"
        ):
            SourceConfig(
                name="places",
                url="http://example.com/data.csv",
                file="data.csv",
                kind=SourceKind.TABULAR,
                separator=",",
                attributes=AttributesConfig(
                    original=[OriginalAttributeConfig(name="id", type=DataType.INTEGER)]
                ),
                features=FeatureConfig(
                    identifier=[IdentifierColumnConfig(column="other.id")],
                    names=[NameColumnConfig(column="places.id")],
                ),
            )


@pytest.mark.unit
class TestGazetteerConfig:
    """Test GazetteerConfig model."""

    def test_creates_with_valid_name(self):
        """Test creating with valid gazetteer name."""
        # Act
        config = GazetteerConfig(
            name="test_gazetteer",
            sources=[
                SourceConfig(
                    name="source1",
                    url="http://example.com/data.csv",
                    file="data.csv",
                    kind=SourceKind.TABULAR,
                    separator=",",
                    attributes=AttributesConfig(
                        original=[
                            OriginalAttributeConfig(name="id", type=DataType.INTEGER)
                        ]
                    ),
                )
            ],
        )

        # Assert
        assert config.name == "test_gazetteer"
        assert len(config.sources) == 1

    def test_accepts_name_with_hyphens(self):
        """Test that gazetteer name with hyphens is accepted."""
        config = GazetteerConfig(
            name="test-gazetteer",
            sources=[],
        )

        assert config.name == "test-gazetteer"

    def test_rejects_name_with_spaces(self):
        """Test that gazetteer name with spaces is rejected."""
        # Act & Assert
        with pytest.raises(
            ValueError,
            match="Gazetteer name must contain only alphanumeric characters, "
            "underscores, and hyphens",
        ):
            GazetteerConfig(
                name="test gazetteer",
                sources=[],
            )

    def test_rejects_name_with_other_special_characters(self):
        """Test that gazetteer name with other special characters is rejected."""
        with pytest.raises(
            ValueError,
            match="Gazetteer name must contain only alphanumeric characters, "
            "underscores, and hyphens",
        ):
            GazetteerConfig(
                name="test.gazetteer",
                sources=[],
            )

    def test_rejects_duplicate_source_names(self):
        """Test that duplicate source names are rejected."""
        # Act & Assert
        with pytest.raises(ValueError, match="Source names must be unique"):
            GazetteerConfig(
                name="test_gaz",
                sources=[
                    SourceConfig(
                        name="source1",
                        url="http://example.com/data1.csv",
                        file="data1.csv",
                        kind=SourceKind.TABULAR,
                        separator=",",
                        attributes=AttributesConfig(
                            original=[
                                OriginalAttributeConfig(
                                    name="id", type=DataType.INTEGER
                                )
                            ]
                        ),
                    ),
                    SourceConfig(
                        name="source1",  # Duplicate!
                        url="http://example.com/data2.csv",
                        file="data2.csv",
                        kind=SourceKind.TABULAR,
                        separator=",",
                        attributes=AttributesConfig(
                            original=[
                                OriginalAttributeConfig(
                                    name="id", type=DataType.INTEGER
                                )
                            ]
                        ),
                    ),
                ],
            )

    def test_validates_view_select_references(self):
        """Test that view select references must point to existing sources."""
        # Act & Assert
        with pytest.raises(ValueError, match="select references non-existent source"):
            GazetteerConfig(
                name="test_gaz",
                sources=[
                    SourceConfig(
                        name="source1",
                        url="http://example.com/data.csv",
                        file="data.csv",
                        kind=SourceKind.TABULAR,
                        separator=",",
                        attributes=AttributesConfig(
                            original=[
                                OriginalAttributeConfig(
                                    name="id", type=DataType.INTEGER
                                )
                            ]
                        ),
                        view=ViewConfig(
                            select=[SelectConfig(column="non_existent_source.col1")]
                        ),
                    )
                ],
            )

    def test_validates_view_join_references(self):
        """Test that view join references must point to existing sources."""
        # Act & Assert
        with pytest.raises(
            ValueError, match="join condition references non-existent source"
        ):
            GazetteerConfig(
                name="test_gaz",
                sources=[
                    SourceConfig(
                        name="source1",
                        url="http://example.com/data.csv",
                        file="data.csv",
                        kind=SourceKind.TABULAR,
                        separator=",",
                        attributes=AttributesConfig(
                            original=[
                                OriginalAttributeConfig(
                                    name="id", type=DataType.INTEGER
                                )
                            ]
                        ),
                        view=ViewConfig(
                            select=[SelectConfig(column="source1.col1")],
                            join=[
                                ViewJoinConfig(
                                    method="left join",
                                    condition=AttributeConditionConfig(
                                        left=JoinOperandConfig(column="source1.id"),
                                        right=JoinOperandConfig(
                                            column="non_existent_source.id"
                                        ),
                                    ),
                                )
                            ],
                        ),
                    )
                ],
            )

    def test_accepts_valid_view_references(self):
        """Test that valid view references are accepted."""
        # Act
        config = GazetteerConfig(
            name="test_gaz",
            sources=[
                SourceConfig(
                    name="source1",
                    url="http://example.com/s1.csv",
                    file="s1.csv",
                    kind=SourceKind.TABULAR,
                    separator=",",
                    attributes=AttributesConfig(
                        original=[
                            OriginalAttributeConfig(name="id", type=DataType.INTEGER)
                        ]
                    ),
                ),
                SourceConfig(
                    name="source2",
                    url="http://example.com/s2.csv",
                    file="s2.csv",
                    kind=SourceKind.TABULAR,
                    separator=",",
                    attributes=AttributesConfig(
                        original=[
                            OriginalAttributeConfig(name="id", type=DataType.INTEGER)
                        ]
                    ),
                    view=ViewConfig(
                        select=[
                            SelectConfig(column="source1.id", alias="s1_id"),
                            SelectConfig(column="source2.id", alias="s2_id"),
                        ],
                        join=[
                            ViewJoinConfig(
                                method="left join",
                                condition=AttributeConditionConfig(
                                    left=JoinOperandConfig(column="source2.ref_id"),
                                    right=JoinOperandConfig(column="source1.id"),
                                ),
                            )
                        ],
                    ),
                ),
            ],
        )

        # Assert
        assert len(config.sources) == 2


@pytest.mark.unit
class TestGazetteerConfigFromYAML:
    """Test GazetteerConfig.from_yaml() method."""

    def test_loads_from_yaml_file(self):
        """Test loading configuration from YAML file."""
        # Arrange
        yaml_content = {
            "name": "test_gazetteer",
            "sources": [
                {
                    "name": "source1",
                    "url": "http://example.com/data.csv",
                    "file": "data.csv",
                    "kind": "tabular",
                    "separator": ",",
                    "attributes": {
                        "original": [{"name": "id", "type": "integer"}],
                    },
                }
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(yaml_content, f)
            temp_path = f.name

        try:
            # Act
            config = GazetteerConfig.from_yaml(temp_path)

            # Assert
            assert config.name == "test_gazetteer"
            assert len(config.sources) == 1
            assert config.sources[0].name == "source1"
        finally:
            Path(temp_path).unlink()

    def test_validates_loaded_yaml(self):
        """Test that loaded YAML is validated."""
        # Arrange
        yaml_content = {
            "name": "test.invalid",  # Invalid name (dot not allowed)
            "sources": [],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(yaml_content, f)
            temp_path = f.name

        try:
            # Act & Assert
            with pytest.raises(ValueError, match="Gazetteer name must contain only"):
                GazetteerConfig.from_yaml(temp_path)
        finally:
            Path(temp_path).unlink()
