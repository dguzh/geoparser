"""
Unit tests for geoparser/gazetteer/installer/model.py

Tests configuration models and validators for gazetteer installation.
"""

import tempfile
from pathlib import Path

import pytest
import yaml

from geoparser.gazetteer.installer.model import (
    AttributesConfig,
    ColumnConfig,
    DataType,
    DerivedAttributeConfig,
    FeatureConfig,
    GazetteerConfig,
    NameColumnConfig,
    OriginalAttributeConfig,
    SelectConfig,
    SourceConfig,
    SourceType,
    ViewConfig,
    ViewJoinConfig,
)


@pytest.mark.unit
class TestDataTypeEnum:
    """Test DataType enum."""

    def test_has_text_type(self):
        """Test that DATA_TYPE has TEXT."""
        assert DataType.TEXT == "TEXT"

    def test_has_integer_type(self):
        """Test that DataType has INTEGER."""
        assert DataType.INTEGER == "INTEGER"

    def test_has_real_type(self):
        """Test that DataType has REAL."""
        assert DataType.REAL == "REAL"

    def test_has_blob_type(self):
        """Test that DataType has BLOB."""
        assert DataType.BLOB == "BLOB"

    def test_has_geometry_type(self):
        """Test that DataType has GEOMETRY."""
        assert DataType.GEOMETRY == "GEOMETRY"


@pytest.mark.unit
class TestSourceTypeEnum:
    """Test SourceType enum."""

    def test_has_tabular_type(self):
        """Test that SourceType has TABULAR."""
        assert SourceType.TABULAR == "tabular"

    def test_has_spatial_type(self):
        """Test that SourceType has SPATIAL."""
        assert SourceType.SPATIAL == "spatial"


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

    def test_creates_with_source_and_column(self):
        """Test creating with source and column."""
        # Act
        select = SelectConfig(source="table1", column="col1")

        # Assert
        assert select.source == "table1"
        assert select.column == "col1"
        assert select.alias is None

    def test_creates_with_alias(self):
        """Test creating with alias."""
        # Act
        select = SelectConfig(source="table1", column="col1", alias="renamed_col")

        # Assert
        assert select.alias == "renamed_col"


@pytest.mark.unit
class TestViewJoinConfig:
    """Test ViewJoinConfig model."""

    def test_creates_with_valid_data(self):
        """Test creating with valid join data."""
        # Act
        join = ViewJoinConfig(
            type="LEFT JOIN",
            source="table2",
            condition="table1.id = table2.ref_id",
        )

        # Assert
        assert join.type == "LEFT JOIN"
        assert join.source == "table2"
        assert join.condition == "table1.id = table2.ref_id"


@pytest.mark.unit
class TestColumnConfig:
    """Test ColumnConfig model."""

    def test_creates_with_column_name(self):
        """Test creating with column name."""
        # Act
        col = ColumnConfig(column="id")

        # Assert
        assert col.column == "id"


@pytest.mark.unit
class TestNameColumnConfig:
    """Test NameColumnConfig model."""

    def test_creates_without_separator(self):
        """Test creating without separator."""
        # Act
        name_col = NameColumnConfig(column="name")

        # Assert
        assert name_col.column == "name"
        assert name_col.separator is None

    def test_creates_with_separator(self):
        """Test creating with separator."""
        # Act
        name_col = NameColumnConfig(column="names", separator=",")

        # Assert
        assert name_col.separator == ","


@pytest.mark.unit
class TestFeatureConfig:
    """Test FeatureConfig model."""

    def test_creates_with_identifier_and_names(self):
        """Test creating with identifier and names."""
        # Act
        feature = FeatureConfig(
            identifier=[ColumnConfig(column="id")],
            names=[NameColumnConfig(column="name")],
        )

        # Assert
        assert len(feature.identifier) == 1
        assert len(feature.names) == 1


@pytest.mark.unit
class TestViewConfig:
    """Test ViewConfig model."""

    def test_creates_with_select_only(self):
        """Test creating with select only."""
        # Act
        view = ViewConfig(select=[SelectConfig(source="table1", column="col1")])

        # Assert
        assert len(view.select) == 1
        assert view.join is None

    def test_creates_with_join(self):
        """Test creating with join."""
        # Act
        view = ViewConfig(
            select=[SelectConfig(source="t1", column="col1")],
            join=[
                ViewJoinConfig(type="LEFT JOIN", source="t2", condition="t1.id=t2.id")
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
            type=SourceType.TABULAR,
            separator="\t",
            attributes=AttributesConfig(
                original=[OriginalAttributeConfig(name="id", type=DataType.INTEGER)]
            ),
        )

        # Assert
        assert source.name == "test_source"
        assert source.url == "http://example.com/data.csv"
        assert source.type == SourceType.TABULAR
        assert source.separator == "\t"

    def test_creates_tabular_source_with_path(self):
        """Test creating tabular source with local path."""
        # Act
        source = SourceConfig(
            name="test_source",
            path="/local/data.csv",
            file="data.csv",
            type=SourceType.TABULAR,
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
                type=SourceType.TABULAR,
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
                type=SourceType.TABULAR,
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
                type=SourceType.TABULAR,
                attributes=AttributesConfig(
                    original=[OriginalAttributeConfig(name="id", type=DataType.INTEGER)]
                ),
            )

    def test_tabular_rejects_layer(self):
        """Test that tabular sources cannot have layer."""
        # Act & Assert
        with pytest.raises(
            ValueError, match="Layer can not be specified for tabular sources"
        ):
            SourceConfig(
                name="test",
                url="http://example.com/data.csv",
                file="data.csv",
                type=SourceType.TABULAR,
                separator=",",
                layer="layer0",
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
                type=SourceType.SPATIAL,
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
                type=SourceType.SPATIAL,
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
                type=SourceType.SPATIAL,
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
            type=SourceType.SPATIAL,
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
        assert source.type == SourceType.SPATIAL

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
                type=SourceType.TABULAR,
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
                type=SourceType.SPATIAL,
                attributes=AttributesConfig(
                    original=[
                        OriginalAttributeConfig(
                            name="geom", type=DataType.GEOMETRY, srid=4326
                        )
                    ]
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
                    type=SourceType.TABULAR,
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

    def test_rejects_name_with_special_characters(self):
        """Test that gazetteer name with special characters is rejected."""
        # Act & Assert
        with pytest.raises(
            ValueError,
            match="Gazetteer name must contain only alphanumeric characters and underscores",
        ):
            GazetteerConfig(
                name="test-gazetteer",  # Hyphen not allowed
                sources=[],
            )

    def test_rejects_name_with_spaces(self):
        """Test that gazetteer name with spaces is rejected."""
        # Act & Assert
        with pytest.raises(
            ValueError,
            match="Gazetteer name must contain only alphanumeric characters and underscores",
        ):
            GazetteerConfig(
                name="test gazetteer",
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
                        type=SourceType.TABULAR,
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
                        type=SourceType.TABULAR,
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
                        type=SourceType.TABULAR,
                        separator=",",
                        attributes=AttributesConfig(
                            original=[
                                OriginalAttributeConfig(
                                    name="id", type=DataType.INTEGER
                                )
                            ]
                        ),
                        view=ViewConfig(
                            select=[
                                SelectConfig(
                                    source="non_existent_source", column="col1"
                                )
                            ]
                        ),
                    )
                ],
            )

    def test_validates_view_join_references(self):
        """Test that view join references must point to existing sources."""
        # Act & Assert
        with pytest.raises(ValueError, match="join references non-existent source"):
            GazetteerConfig(
                name="test_gaz",
                sources=[
                    SourceConfig(
                        name="source1",
                        url="http://example.com/data.csv",
                        file="data.csv",
                        type=SourceType.TABULAR,
                        separator=",",
                        attributes=AttributesConfig(
                            original=[
                                OriginalAttributeConfig(
                                    name="id", type=DataType.INTEGER
                                )
                            ]
                        ),
                        view=ViewConfig(
                            select=[SelectConfig(source="source1", column="col1")],
                            join=[
                                ViewJoinConfig(
                                    type="LEFT JOIN",
                                    source="non_existent_source",
                                    condition="source1.id = non_existent_source.id",
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
                    type=SourceType.TABULAR,
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
                    type=SourceType.TABULAR,
                    separator=",",
                    attributes=AttributesConfig(
                        original=[
                            OriginalAttributeConfig(name="id", type=DataType.INTEGER)
                        ]
                    ),
                    view=ViewConfig(
                        select=[
                            SelectConfig(source="source1", column="id", alias="s1_id"),
                            SelectConfig(source="source2", column="id", alias="s2_id"),
                        ],
                        join=[
                            ViewJoinConfig(
                                type="LEFT JOIN",
                                source="source1",
                                condition="source2.ref_id = source1.id",
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
                    "type": "tabular",
                    "separator": ",",
                    "attributes": {
                        "original": [{"name": "id", "type": "INTEGER"}],
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
            "name": "test-invalid",  # Invalid name
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
