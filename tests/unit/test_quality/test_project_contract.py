import re
from pathlib import Path

import pytest
import yaml

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised on Python 3.10 CI.
    import tomli as tomllib

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
    assert any(
        dependency.startswith("tomli") and 'python_version < "3.11"' in dependency
        for dependency in test_dependencies
        if isinstance(dependency, str)
    )

    marker_names = {
        marker.split(":", maxsplit=1)[0].strip()
        for marker in project["tool"]["pytest"]["ini_options"]["markers"]
    }
    assert {"property", "acceptance", "architecture"} <= marker_names
    assert (
        project["tool"]["pytest"]["ini_options"]["tmp_path_retention_policy"]
        == "failed"
    )


def test_mutation_runner_copies_quality_support_modules() -> None:
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as pyproject_file:
        project = tomllib.load(pyproject_file)

    copied_paths = set(project["tool"]["mutmut"]["also_copy"])
    assert {
        "docs",
        "scripts",
        ".github",
        ".dockerignore",
        "CITATION.cff",
        "Dockerfile",
        "mkdocs.yml",
    } <= copied_paths


def test_public_documentation_uses_strict_mkdocs_material() -> None:
    configuration = PROJECT_ROOT / "mkdocs.yml"
    assert configuration.is_file()
    content = configuration.read_text(encoding="utf-8")
    parsed = yaml.safe_load(content)

    assert "site_name: Irchel Geoparser" in content
    assert "site_url: https://docs.geoparser.app/" in content
    assert "strict: true" in content
    assert "mkdocstrings" in content
    assert "- Home: index.md" in content
    assert parsed["strict"] is True
    assert parsed["plugins"][1] == {
        "mkdocstrings": {
            "handlers": {
                "python": {
                    "options": {
                        "allow_inspection": True,
                        "annotations_path": "brief",
                        "docstring_section_style": "table",
                        "docstring_style": "google",
                        "docstring_options": {
                            "warn_missing_types": False,
                            "warn_unknown_params": False,
                        },
                        "force_inspection": True,
                        "members_order": "source",
                        "separate_signature": True,
                        "show_object_full_path": False,
                        "show_root_heading": True,
                        "show_source": False,
                    }
                }
            }
        }
    }
    assert not list((PROJECT_ROOT / "docs").rglob("*.rst"))

    def nav_paths(items: list[object]) -> list[str]:
        paths: list[str] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            for value in item.values():
                if isinstance(value, str) and value.endswith(".md"):
                    paths.append(value)
                elif isinstance(value, list):
                    paths.extend(nav_paths(value))
        return paths

    for relative_path in nav_paths(parsed["nav"]):
        assert (PROJECT_ROOT / "docs" / relative_path).is_file(), relative_path


def test_pyproject_is_compatible_with_mutmut_legacy_toml_parser() -> None:
    legacy_toml = pytest.importorskip("toml")

    legacy_toml.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_runtime_packaging_is_locked_and_does_not_copy_local_state() -> None:
    dockerfile = PROJECT_ROOT / "Dockerfile"
    dockerignore = PROJECT_ROOT / ".dockerignore"
    citation = PROJECT_ROOT / "CITATION.cff"
    pyproject = PROJECT_ROOT / "pyproject.toml"

    assert dockerfile.is_file()
    assert dockerignore.is_file()
    assert citation.is_file()

    dockerfile_content = dockerfile.read_text(encoding="utf-8")
    dockerignore_content = dockerignore.read_text(encoding="utf-8")
    assert "python:3.12-slim" in dockerfile_content
    assert "uv sync --locked --no-dev" in dockerfile_content
    assert 'CMD ["python", "-m", "geoparser", "--help"]' in dockerfile_content
    assert ".git" in dockerignore_content
    assert ".venv" in dockerignore_content
    assert "secrets" in dockerignore_content

    pyproject_content = pyproject.read_text(encoding="utf-8")
    assert 'name = "pytorch-cpu"' in pyproject_content
    assert 'url = "https://download.pytorch.org/whl/cpu"' in pyproject_content

    with (PROJECT_ROOT / "uv.lock").open("rb") as lockfile:
        lock = tomllib.load(lockfile)
    cpu_torch = [
        package
        for package in lock["package"]
        if package["name"] == "torch"
        and package.get("source", {}).get("registry")
        == "https://download.pytorch.org/whl/cpu"
    ]
    assert cpu_torch
    assert not any(
        package["name"].startswith(("cuda-", "nvidia-")) for package in lock["package"]
    )

    citation_data = yaml.safe_load(citation.read_text(encoding="utf-8"))
    assert citation_data["cff-version"] == "1.2.0"
    assert citation_data["title"] == "Irchel Geoparser"
    assert citation_data["version"] == "0.6.0"
    assert citation_data["license"] == "MIT"
    assert citation_data["repository-code"].startswith("https://github.com/")
    assert len(citation_data["authors"]) >= 1


def test_ci_runs_the_full_gate_and_publishes_strict_mkdocs() -> None:
    quality = (PROJECT_ROOT / ".github/workflows/quality.yml").read_text(
        encoding="utf-8"
    )
    docs = (PROJECT_ROOT / ".github/workflows/docs.yml").read_text(encoding="utf-8")

    assert "pull_request:" in quality
    assert "uv sync --locked" in quality
    assert "scripts/quality_gauntlet.py" in quality
    assert "--skip-mutation" not in quality
    assert "--skip-docker" not in quality
    assert "mkdocs build --strict" in docs
    assert "deploy-pages" in docs


def test_ci_pins_setup_uv_to_a_resolvable_release() -> None:
    workflow_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((PROJECT_ROOT / ".github/workflows").glob("*.yml"))
    )

    assert "astral-sh/setup-uv@v10.1.0" in workflow_text
    assert "astral-sh/setup-uv@v10\n" not in workflow_text
