from pathlib import Path

import pytest

from scripts.check_architecture import (
    FORBIDDEN_IMPORTS,
    build_import_graph,
    find_boundary_violations,
    find_cycles,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _module(root: Path, name: str, source: str) -> None:
    path = root / f"{name.replace('.', '/')}.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


@pytest.mark.architecture
def test_import_graph_contains_runtime_internal_imports(tmp_path: Path) -> None:
    package = tmp_path / "pkg"
    _module(package, "__init__", "")
    _module(package, "a", "from pkg.b import value\n")
    _module(package, "b", "value = 1\n")

    graph = build_import_graph(package, "pkg")

    assert graph["pkg.a"] == {"pkg.b"}
    assert graph["pkg.b"] == set()


@pytest.mark.architecture
def test_type_checking_imports_do_not_create_runtime_edges(tmp_path: Path) -> None:
    package = tmp_path / "pkg"
    _module(package, "__init__", "")
    _module(
        package,
        "a",
        "from typing import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n"
        "    from pkg.b import Value\n",
    )
    _module(package, "b", "Value = int\n")

    graph = build_import_graph(package, "pkg")

    assert graph["pkg.a"] == set()


@pytest.mark.architecture
def test_find_cycles_reports_a_deterministic_cycle(tmp_path: Path) -> None:
    package = tmp_path / "pkg"
    _module(package, "__init__", "")
    _module(package, "a", "from pkg.b import value\n")
    _module(package, "b", "from pkg.c import value\n")
    _module(package, "c", "from pkg.a import value\n")

    cycles = find_cycles(build_import_graph(package, "pkg"))

    assert cycles == [("pkg.a", "pkg.b", "pkg.c", "pkg.a")]


@pytest.mark.architecture
def test_find_boundary_violations_reports_forbidden_edges(tmp_path: Path) -> None:
    package = tmp_path / "pkg"
    _module(package, "__init__", "")
    _module(package, "db", "from pkg.modules import value\n")
    _module(package, "modules", "value = 1\n")

    graph = build_import_graph(package, "pkg")
    forbidden = {"pkg.db": {"pkg.modules"}}

    assert find_boundary_violations(graph, forbidden) == [("pkg.db", "pkg.modules")]


@pytest.mark.architecture
def test_real_package_has_no_cycles_or_boundary_violations() -> None:
    graph = build_import_graph(PROJECT_ROOT / "geoparser", "geoparser")

    assert find_cycles(graph) == []
    assert find_boundary_violations(graph, FORBIDDEN_IMPORTS) == []
