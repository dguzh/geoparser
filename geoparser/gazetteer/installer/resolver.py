from typing import Dict, List, Set

from geoparser.gazetteer.model import SourceConfig

# Type alias for dependency graph structure
Graph = Dict[str, Set[str]]


class DependencyResolver:
    """Resolves dependencies between sources based on view joins."""

    def resolve(self, sources: List[SourceConfig]) -> List[SourceConfig]:
        """
        Resolve dependencies and return sources in topological order.

        Sources with views that join other sources will be ordered after
        their dependencies.

        Args:
            sources: List of source configurations

        Returns:
            List of sources in dependency order

        Raises:
            ValueError: If circular dependencies are detected
        """
        # Build dependency graph
        graph = self._build_dependency_graph(sources)

        # Perform topological sort
        return self._topological_sort(sources, graph)

    def _build_dependency_graph(self, sources: List[SourceConfig]) -> Graph:
        """
        Build a dependency graph from source configurations.

        The graph maps source names to sets of sources they depend on.
        For example, if source 'admin_areas' joins with 'countries',
        the graph will contain: {'admin_areas': {'countries'}}.

        Args:
            sources: List of source configurations

        Returns:
            Dependency graph {source_name: {dependency1, dependency2, ...}}
        """
        graph: Graph = {source.name: set() for source in sources}

        for source in sources:
            if source.view is None:
                continue

            # Extract dependencies from view joins
            if source.view.join:
                for join_item in source.view.join:
                    # Source depends on the joined source
                    if join_item.source != source.name:
                        graph[source.name].add(join_item.source)

            # Also check select clause for dependencies
            for select_item in source.view.select:
                # If selecting from a different source, add dependency
                if select_item.source != source.name:
                    graph[source.name].add(select_item.source)

        return graph

    def _topological_sort(
        self, sources: List[SourceConfig], graph: Graph
    ) -> List[SourceConfig]:
        """
        Perform topological sort on the dependency graph.

        Uses Kahn's algorithm for topological sorting.

        Args:
            sources: List of source configurations
            graph: Dependency graph

        Returns:
            Sources in topological order

        Raises:
            ValueError: If circular dependencies are detected
        """
        # Create a mapping from name to source config
        source_map = {source.name: source for source in sources}

        # Calculate in-degrees (number of sources each source depends on)
        in_degree = {name: len(dependencies) for name, dependencies in graph.items()}

        # Start with sources that have no dependencies
        queue = [name for name, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            # Sort queue to ensure deterministic ordering when there are no dependencies
            queue.sort()

            # Process next source (one with no remaining dependencies)
            current = queue.pop(0)
            result.append(source_map[current])

            # For each source that depends on the current source, remove that dependency
            for source_name, dependencies in graph.items():
                if current in dependencies:
                    dependencies.remove(current)
                    in_degree[source_name] -= 1
                    if in_degree[source_name] == 0:
                        queue.append(source_name)

        # Check if all sources were processed
        if len(result) != len(sources):
            # Circular dependency detected
            unprocessed = set(source_map.keys()) - {s.name for s in result}
            raise ValueError(
                f"Circular dependency detected among sources: {unprocessed}"
            )

        return result
