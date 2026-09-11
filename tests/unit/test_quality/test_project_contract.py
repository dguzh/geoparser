import re
import tomllib
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _package_name(requirement: str) -> str:
    return re.split(r"[\[<>=!~;]", requirement, maxsplit=1)[0].strip().lower()


def test_project_quality_dependencies_and_pytest_markers_are_declared() -> None:
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as pyproject_file:
        project = tomllib.load(pyproject_file)

    test_dependencies = project["dependency-groups"]["test"]
    dependency_names = {
        _package_name(dependency)
        for dependency in test_dependencies
        if isinstance(dependency, str)
    }
    assert {"hypothesis", "pytest-bdd"} <= dependency_names

    marker_names = {
        marker.split(":", maxsplit=1)[0].strip()
        for marker in project["tool"]["pytest"]["ini_options"]["markers"]
    }
    assert {"property", "acceptance", "architecture"} <= marker_names
