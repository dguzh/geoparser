"""
Unit tests for geoparser/gazetteer/installer/utils/dependency.py

Tests the DependencyResolver class for topological sorting of sources.
"""

import pytest

from geoparser.gazetteer.installer.model import (
    AttributesConfig,
    DataType,
    OriginalAttributeConfig,
    SelectConfig,
    SourceConfig,
    SourceType,
    ViewConfig,
    ViewJoinConfig,
)
from geoparser.gazetteer.installer.utils.dependency import DependencyResolver


@pytest.mark.unit
class TestDependencyResolverResolve:
    """Test DependencyResolver.resolve() method."""

    def test_resolves_sources_with_no_dependencies(self):
        """Test that sources with no dependencies are returned in original order."""
        # Arrange
        source1 = SourceConfig(
            name="source1",
            url="http://example.com/data1.csv",
            file="data1.csv",
            type=SourceType.TABULAR,
            separator=",",
            attributes=AttributesConfig(
                original=[OriginalAttributeConfig(name="id", type=DataType.INTEGER)]
            ),
        )
        source2 = SourceConfig(
            name="source2",
            url="http://example.com/data2.csv",
            file="data2.csv",
            type=SourceType.TABULAR,
            separator=",",
            attributes=AttributesConfig(
                original=[OriginalAttributeConfig(name="id", type=DataType.INTEGER)]
            ),
        )

        resolver = DependencyResolver()

        # Act
        result = resolver.resolve([source1, source2])

        # Assert
        assert len(result) == 2
        # Since they have no dependencies, order is alphabetical (deterministic)
        assert result[0].name == "source1"
        assert result[1].name == "source2"

    def test_resolves_simple_dependency_chain(self):
        """Test that sources are ordered with dependencies first."""
        # Arrange
        # source2 depends on source1 via view select
        source1 = SourceConfig(
            name="source1",
            url="http://example.com/data1.csv",
            file="data1.csv",
            type=SourceType.TABULAR,
            separator=",",
            attributes=AttributesConfig(
                original=[OriginalAttributeConfig(name="id", type=DataType.INTEGER)]
            ),
        )
        source2 = SourceConfig(
            name="source2",
            url="http://example.com/data2.csv",
            file="data2.csv",
            type=SourceType.TABULAR,
            separator=",",
            attributes=AttributesConfig(
                original=[OriginalAttributeConfig(name="ref_id", type=DataType.INTEGER)]
            ),
            view=ViewConfig(select=[SelectConfig(source="source1", column="id")]),
        )

        resolver = DependencyResolver()

        # Act - note we pass source2 first to test reordering
        result = resolver.resolve([source2, source1])

        # Assert
        assert len(result) == 2
        assert result[0].name == "source1"  # Dependency should come first
        assert result[1].name == "source2"

    def test_resolves_join_dependencies(self):
        """Test that sources with join dependencies are ordered correctly."""
        # Arrange
        source1 = SourceConfig(
            name="source1",
            url="http://example.com/data1.csv",
            file="data1.csv",
            type=SourceType.TABULAR,
            separator=",",
            attributes=AttributesConfig(
                original=[OriginalAttributeConfig(name="id", type=DataType.INTEGER)]
            ),
        )
        source2 = SourceConfig(
            name="source2",
            url="http://example.com/data2.csv",
            file="data2.csv",
            type=SourceType.TABULAR,
            separator=",",
            attributes=AttributesConfig(
                original=[OriginalAttributeConfig(name="id", type=DataType.INTEGER)]
            ),
            view=ViewConfig(
                select=[SelectConfig(source="source2", column="id")],
                join=[
                    ViewJoinConfig(
                        type="LEFT JOIN",
                        source="source1",
                        condition="source2.id = source1.id",
                    )
                ],
            ),
        )

        resolver = DependencyResolver()

        # Act
        result = resolver.resolve([source2, source1])

        # Assert
        assert result[0].name == "source1"
        assert result[1].name == "source2"

    def test_resolves_complex_dependency_graph(self):
        """Test resolving a complex multi-level dependency graph."""
        # Arrange
        # source1 has no dependencies
        # source2 depends on source1
        # source3 depends on source1 and source2
        source1 = SourceConfig(
            name="source1",
            url="http://example.com/data1.csv",
            file="data1.csv",
            type=SourceType.TABULAR,
            separator=",",
            attributes=AttributesConfig(
                original=[OriginalAttributeConfig(name="id", type=DataType.INTEGER)]
            ),
        )
        source2 = SourceConfig(
            name="source2",
            url="http://example.com/data2.csv",
            file="data2.csv",
            type=SourceType.TABULAR,
            separator=",",
            attributes=AttributesConfig(
                original=[OriginalAttributeConfig(name="id", type=DataType.INTEGER)]
            ),
            view=ViewConfig(select=[SelectConfig(source="source1", column="id")]),
        )
        source3 = SourceConfig(
            name="source3",
            url="http://example.com/data3.csv",
            file="data3.csv",
            type=SourceType.TABULAR,
            separator=",",
            attributes=AttributesConfig(
                original=[OriginalAttributeConfig(name="id", type=DataType.INTEGER)]
            ),
            view=ViewConfig(
                select=[
                    SelectConfig(source="source1", column="id", alias="s1_id"),
                    SelectConfig(source="source2", column="id", alias="s2_id"),
                ]
            ),
        )

        resolver = DependencyResolver()

        # Act - pass in reverse order
        result = resolver.resolve([source3, source2, source1])

        # Assert
        assert len(result) == 3
        assert result[0].name == "source1"  # No dependencies
        assert result[1].name == "source2"  # Depends on source1
        assert result[2].name == "source3"  # Depends on source1 and source2

    def test_detects_circular_dependency(self):
        """Test that circular dependencies are detected and raise an error."""
        # Arrange
        # source1 depends on source2, source2 depends on source1
        source1 = SourceConfig(
            name="source1",
            url="http://example.com/data1.csv",
            file="data1.csv",
            type=SourceType.TABULAR,
            separator=",",
            attributes=AttributesConfig(
                original=[OriginalAttributeConfig(name="id", type=DataType.INTEGER)]
            ),
            view=ViewConfig(select=[SelectConfig(source="source2", column="id")]),
        )
        source2 = SourceConfig(
            name="source2",
            url="http://example.com/data2.csv",
            file="data2.csv",
            type=SourceType.TABULAR,
            separator=",",
            attributes=AttributesConfig(
                original=[OriginalAttributeConfig(name="id", type=DataType.INTEGER)]
            ),
            view=ViewConfig(select=[SelectConfig(source="source1", column="id")]),
        )

        resolver = DependencyResolver()

        # Act & Assert
        with pytest.raises(ValueError, match="Circular dependency detected"):
            resolver.resolve([source1, source2])

    def test_ignores_self_references_in_views(self):
        """Test that self-references in views are ignored."""
        # Arrange
        source1 = SourceConfig(
            name="source1",
            url="http://example.com/data1.csv",
            file="data1.csv",
            type=SourceType.TABULAR,
            separator=",",
            attributes=AttributesConfig(
                original=[OriginalAttributeConfig(name="id", type=DataType.INTEGER)]
            ),
            view=ViewConfig(
                select=[
                    SelectConfig(source="source1", column="id"),  # Self-reference
                    SelectConfig(source="source1", column="name"),  # Self-reference
                ]
            ),
        )

        resolver = DependencyResolver()

        # Act
        result = resolver.resolve([source1])

        # Assert
        assert len(result) == 1
        assert result[0].name == "source1"


@pytest.mark.unit
class TestDependencyResolverBuildDependencyGraph:
    """Test DependencyResolver._build_dependency_graph() method."""

    def test_builds_empty_graph_for_no_views(self):
        """Test that sources without views have empty dependency sets."""
        # Arrange
        source1 = SourceConfig(
            name="source1",
            url="http://example.com/data1.csv",
            file="data1.csv",
            type=SourceType.TABULAR,
            separator=",",
            attributes=AttributesConfig(
                original=[OriginalAttributeConfig(name="id", type=DataType.INTEGER)]
            ),
        )

        resolver = DependencyResolver()

        # Act
        graph = resolver._build_dependency_graph([source1])

        # Assert
        assert "source1" in graph
        assert len(graph["source1"]) == 0

    def test_extracts_select_dependencies(self):
        """Test that dependencies from select clauses are extracted."""
        # Arrange
        source1 = SourceConfig(
            name="source1",
            url="http://example.com/data1.csv",
            file="data1.csv",
            type=SourceType.TABULAR,
            separator=",",
            attributes=AttributesConfig(
                original=[OriginalAttributeConfig(name="id", type=DataType.INTEGER)]
            ),
        )
        source2 = SourceConfig(
            name="source2",
            url="http://example.com/data2.csv",
            file="data2.csv",
            type=SourceType.TABULAR,
            separator=",",
            attributes=AttributesConfig(
                original=[OriginalAttributeConfig(name="id", type=DataType.INTEGER)]
            ),
            view=ViewConfig(select=[SelectConfig(source="source1", column="id")]),
        )

        resolver = DependencyResolver()

        # Act
        graph = resolver._build_dependency_graph([source1, source2])

        # Assert
        assert "source1" in graph["source2"]

    def test_extracts_join_dependencies(self):
        """Test that dependencies from join clauses are extracted."""
        # Arrange
        source1 = SourceConfig(
            name="source1",
            url="http://example.com/data1.csv",
            file="data1.csv",
            type=SourceType.TABULAR,
            separator=",",
            attributes=AttributesConfig(
                original=[OriginalAttributeConfig(name="id", type=DataType.INTEGER)]
            ),
        )
        source2 = SourceConfig(
            name="source2",
            url="http://example.com/data2.csv",
            file="data2.csv",
            type=SourceType.TABULAR,
            separator=",",
            attributes=AttributesConfig(
                original=[OriginalAttributeConfig(name="id", type=DataType.INTEGER)]
            ),
            view=ViewConfig(
                select=[SelectConfig(source="source2", column="id")],
                join=[
                    ViewJoinConfig(
                        type="INNER JOIN",
                        source="source1",
                        condition="source2.id = source1.id",
                    )
                ],
            ),
        )

        resolver = DependencyResolver()

        # Act
        graph = resolver._build_dependency_graph([source1, source2])

        # Assert
        assert "source1" in graph["source2"]
