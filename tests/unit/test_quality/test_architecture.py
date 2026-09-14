from pathlib import Path

import pytest

from scripts import check_architecture
from scripts.check_architecture import (
    FORBIDDEN_IMPORTS,
    PURE_MODULES,
    build_import_graph,
    find_boundary_violations,
    find_cycles,
    find_impure_modules,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]

# mutmut runs the suite from a rewritten copy of the tree under ``mutants/``,
# where every function has been expanded into numbered variants and the
# generated code carries imports the real source does not. Checks that read
# the real package are meaningless against that copy, and failing there would
# abort the whole mutation run on this test alone.
IN_MUTANT_TREE = "mutants" in PROJECT_ROOT.parts or "mutants" in Path.cwd().parts


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


@pytest.mark.architecture
def test_find_impure_modules_reports_a_non_stdlib_dependency(tmp_path: Path) -> None:
    package = tmp_path / "pkg"
    _module(package, "__init__", "")
    _module(package, "pure", "import torch\n")

    impure = find_impure_modules(package, "pkg", {"pkg.pure"})

    assert impure == [("pkg.pure", "torch")]


@pytest.mark.architecture
def test_find_impure_modules_accepts_a_standard_library_dependency(
    tmp_path: Path,
) -> None:
    package = tmp_path / "pkg"
    _module(package, "__init__", "")
    _module(package, "pure", "import typing\nfrom dataclasses import dataclass\n")

    assert find_impure_modules(package, "pkg", {"pkg.pure"}) == []


@pytest.mark.architecture
def test_find_impure_modules_reports_an_internal_dependency(tmp_path: Path) -> None:
    package = tmp_path / "pkg"
    _module(package, "__init__", "")
    _module(package, "pure", "from pkg.other import thing\n")
    _module(package, "other", "thing = 1\n")

    impure = find_impure_modules(package, "pkg", {"pkg.pure"})

    assert impure == [("pkg.pure", "pkg.other")]


@pytest.mark.architecture
@pytest.mark.skipif(
    IN_MUTANT_TREE, reason="the mutated copy of the tree is not the source"
)
def test_the_pure_modules_of_the_real_package_stay_pure() -> None:
    """
    The domain logic listed in PURE_MODULES imports only the standard library.

    That is what lets it be exercised directly instead of through the models
    its callers happen to load, and it is a property that erodes the moment
    someone reaches for a convenient helper from elsewhere in the package.
    """
    impure = find_impure_modules(PROJECT_ROOT / "geoparser", "geoparser", PURE_MODULES)

    assert impure == []


@pytest.mark.architecture
def test_the_command_line_check_reports_an_impure_module(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    The CLI enforces PURE_MODULES, not only the test suite.

    The quality gauntlet runs this script rather than importing the helpers, so
    a check that exists only in a pytest test leaves the gate weaker than it
    looks: a pure module could gain a torch dependency and the architecture
    stage would still print "passed".
    """
    package = tmp_path / "pkg"
    _module(package, "__init__", "")
    _module(package, "pure", "import torch\n")
    monkeypatch.setattr(check_architecture, "PURE_MODULES", {"pkg.pure"})

    exit_code = check_architecture.main(["--package", str(package)])

    assert exit_code == 1
    assert "pkg.pure" in capsys.readouterr().out


@pytest.mark.architecture
def test_the_command_line_check_passes_when_pure_modules_stay_pure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A stdlib-only pure module keeps the CLI green."""
    package = tmp_path / "pkg"
    _module(package, "__init__", "")
    _module(package, "pure", "from dataclasses import dataclass\n")
    monkeypatch.setattr(check_architecture, "PURE_MODULES", {"pkg.pure"})

    assert check_architecture.main(["--package", str(package)]) == 0
