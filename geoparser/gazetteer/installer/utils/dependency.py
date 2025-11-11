from typing import Dict, List, Set

from geoparser.gazetteer.installer.model import SourceConfig


class DependencyResolver:
    """
    Resolves dependencies between gazetteer sources.

    Sources can depend on other sources through view joins and column
    selections. This resolver performs topological sorting to determine
    the correct processing order.
    """

    def resolve(self, sources: List[SourceConfig]) -> List[SourceConfig]:
        """
        Resolve dependencies and return sources in topological order.

        Sources with views that join or select from other sources will
        be ordered after their dependencies.

        Args:
            sources: List of source configurations

        Returns:
            List of sources in dependency order (dependencies first)

        Raises:
            ValueError: If circular dependencies are detected
        """
        dependency_graph = self._build_dependency_graph(sources)
        return self._topological_sort(sources, dependency_graph)

    def _build_dependency_graph(
        self,
        sources: List[SourceConfig],
    ) -> Dict[str, Set[str]]:
        """
        Build a dependency graph from source configurations.

        The graph maps each source name to a set of source names it
        depends on. For example, if source 'admin_areas' joins with
        'countries', the graph will contain: {'admin_areas': {'countries'}}.

        Args:
            sources: List of source configurations

        Returns:
            Dependency graph mapping source names to their dependencies
        """
        graph: Dict[str, Set[str]] = {source.name: set() for source in sources}

        for source in sources:
            if source.view is None:
                continue

            dependencies = graph[source.name]

            # Extract dependencies from view joins
            if source.view.join:
                for join_item in source.view.join:
                    if join_item.source != source.name:
                        dependencies.add(join_item.source)

            # Extract dependencies from select clause
            for select_item in source.view.select:
                if select_item.source != source.name:
                    dependencies.add(select_item.source)

        return graph

    def _topological_sort(
        self,
        sources: List[SourceConfig],
        graph: Dict[str, Set[str]],
    ) -> List[SourceConfig]:
        """
        Perform topological sort on the dependency graph.

        Uses Kahn's algorithm to produce a linear ordering of sources
        such that for every dependency edge from source A to source B,
        source B appears before source A in the ordering.

        Args:
            sources: List of source configurations
            graph: Dependency graph

        Returns:
            Sources in topological order

        Raises:
            ValueError: If circular dependencies are detected
        """
        # Create mapping from name to source config
        source_map = {source.name: source for source in sources}

        # Calculate in-degree for each source (number of dependencies)
        in_degree = {name: len(deps) for name, deps in graph.items()}

        # Start with sources that have no dependencies
        queue = [name for name, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            # Sort queue for deterministic ordering when multiple sources
            # have no remaining dependencies
            queue.sort()

            # Process next source with no remaining dependencies
            current = queue.pop(0)
            result.append(source_map[current])

            # Update in-degrees for sources depending on current source
            for source_name, dependencies in graph.items():
                if current in dependencies:
                    dependencies.remove(current)
                    in_degree[source_name] -= 1
                    if in_degree[source_name] == 0:
                        queue.append(source_name)

        # Verify all sources were processed
        if len(result) != len(sources):
            unprocessed = set(source_map.keys()) - {s.name for s in result}
            raise ValueError(
                f"Circular dependency detected among sources: {unprocessed}"
            )

        return result
