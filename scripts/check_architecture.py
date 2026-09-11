"""Check import cycles and dependency boundaries in the package."""

from __future__ import annotations

import argparse
import ast
from collections.abc import Iterable, Mapping
from pathlib import Path


FORBIDDEN_IMPORTS: dict[str, set[str]] = {
    "geoparser.db": {
        "geoparser.context",
        "geoparser.modules",
        "geoparser.project",
        "geoparser.services",
    },
    "geoparser.modules": {
        "geoparser.context",
        "geoparser.db",
        "geoparser.project",
        "geoparser.services",
    },
    "geoparser.context": {
        "geoparser.modules",
        "geoparser.project",
        "geoparser.services",
    },
    "geoparser.services": {
        "geoparser.context",
        "geoparser.modules",
        "geoparser.project",
    },
}


def _module_name(path: Path, package_root: Path, package_name: str) -> str:
    relative = path.relative_to(package_root).with_suffix("")
    parts = relative.parts
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join((package_name, *parts))


def _is_type_checking_test(test: ast.expr) -> bool:
    """Return whether an ``if`` condition is a TYPE_CHECKING guard."""
    if isinstance(test, ast.Name):
        return test.id == "TYPE_CHECKING"
    if isinstance(test, ast.Attribute):
        return test.attr == "TYPE_CHECKING"
    return False


class _ImportVisitor(ast.NodeVisitor):
    """Collect imports while excluding annotation-only imports."""

    def __init__(self) -> None:
        self.runtime: list[tuple[str | None, int, str | None, tuple[str, ...]]] = []

    def visit_If(self, node: ast.If) -> None:
        if _is_type_checking_test(node.test):
            return
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.runtime.append((alias.name, node.lineno, None, ()))

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        self.runtime.append(
            (
                node.module,
                node.lineno,
                "." * node.level,
                tuple(alias.name for alias in node.names),
            )
        )


def _resolve_from_import(
    current: str,
    module: str | None,
    dots: str | None,
    names: tuple[str, ...],
    packages: set[str],
) -> Iterable[str]:
    """Yield import targets that correspond to real internal modules."""
    if dots == "":
        base = module or ""
    else:
        level = len(dots)
        current_parts = current.split(".")
        current_is_package = current in packages
        parent_parts = current_parts if current_is_package else current_parts[:-1]
        base_parts = parent_parts[: len(parent_parts) - level + 1]
        base = ".".join(base_parts)
        if module:
            base = f"{base}.{module}" if base else module

    for name in names:
        exact = f"{base}.{name}" if base else name
        target = exact if exact in packages else base
        if target in packages:
            yield target


def build_import_graph(package_root: Path, package_name: str) -> dict[str, set[str]]:
    """Build a deterministic runtime import graph for one Python package."""
    package_root = package_root.resolve()
    files = sorted(package_root.rglob("*.py"))
    modules = {
        _module_name(path, package_root, package_name): path for path in files
    }
    graph = {module: set() for module in modules}
    packages = set(modules)

    for module, path in modules.items():
        visitor = _ImportVisitor()
        visitor.visit(ast.parse(path.read_text(encoding="utf-8"), filename=str(path)))
        for imported, _, dots, names in visitor.runtime:
            if dots is None:
                if imported and (
                    imported == package_name or imported.startswith(f"{package_name}.")
                ):
                    if imported in packages:
                        graph[module].add(imported)
                continue
            graph[module].update(
                target
                for target in _resolve_from_import(
                    module, imported, dots, names, packages
                )
                if target == package_name or target.startswith(f"{package_name}.")
            )
    return graph


def find_cycles(graph: Mapping[str, set[str]]) -> list[tuple[str, ...]]:
    """Return deterministic cycles, with the repeated start node at the end."""
    cycles: set[tuple[str, ...]] = set()
    visited: set[str] = set()
    stack: list[str] = []
    positions: dict[str, int] = {}

    def visit(node: str) -> None:
        if node in positions:
            start = positions[node]
            cycles.add(tuple((*stack[start:], node)))
            return
        if node in visited:
            return
        positions[node] = len(stack)
        stack.append(node)
        for target in sorted(graph.get(node, set())):
            visit(target)
        stack.pop()
        positions.pop(node)
        visited.add(node)

    for node in sorted(graph):
        visit(node)
    return sorted(cycles)


def find_boundary_violations(
    graph: Mapping[str, set[str]],
    forbidden: Mapping[str, set[str]],
) -> list[tuple[str, str]]:
    """Return runtime edges that cross a forbidden package boundary."""
    violations: set[tuple[str, str]] = set()
    for source in sorted(graph):
        for boundary, blocked in forbidden.items():
            if source != boundary and not source.startswith(f"{boundary}."):
                continue
            for target in graph[source]:
                if any(
                    target == prefix or target.startswith(f"{prefix}.")
                    for prefix in blocked
                ):
                    violations.add((source, target))
    return sorted(violations)


def main(argv: list[str] | None = None) -> int:
    """Check the package and return non-zero when its architecture is invalid."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, default=Path("geoparser"))
    args = parser.parse_args(argv)

    package_root = args.package.resolve()
    package_name = package_root.name
    graph = build_import_graph(package_root, package_name)
    cycles = find_cycles(graph)
    violations = find_boundary_violations(graph, FORBIDDEN_IMPORTS)

    if cycles:
        print("Import cycles:")
        for cycle in cycles:
            print(f"  {' -> '.join(cycle)}")
    if violations:
        print("Forbidden dependency edges:")
        for source, target in violations:
            print(f"  {source} -> {target}")
    if cycles or violations:
        return 1

    print(f"Architecture checks passed for {package_name} ({len(graph)} modules).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
