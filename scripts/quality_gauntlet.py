"""Run the repository's deterministic quality stages in order."""

from __future__ import annotations

import argparse
import os
import subprocess
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

Command = tuple[str, ...]


@dataclass(frozen=True)
class Stage:
    """A named group of commands that share one working directory."""

    name: str
    commands: tuple[Command, ...]
    cwd: Path


def _uv(*arguments: str) -> Command:
    return ("uv", "run", "--no-sync", *arguments)


def build_stages(
    root: Path,
    artifact_dir: Path,
    *,
    skip_mutation: bool = False,
    skip_docker: bool = False,
    docker_tag: str = "geoparser:quality-check",
) -> list[Stage]:
    """Build the ordered quality stages for a repository checkout."""
    root = root.resolve()
    artifact_dir = artifact_dir.resolve()
    coverage_report = artifact_dir / "coverage-html"
    coverage_data = artifact_dir / ".coverage"

    stages = [
        Stage("baseline", (_uv("pytest", "--cov-fail-under=100"),), root),
        Stage(
            "ruff",
            (
                _uv("ruff", "check", "."),
                _uv("ruff", "format", "--check", "."),
            ),
            root,
        ),
        Stage("ty", (_uv("ty", "check", "geoparser", "scripts", "tests"),), root),
        Stage(
            "dependencies",
            (
                ("uv", "lock", "--check"),
                _uv(
                    "deptry",
                    "geoparser",
                    "demo",
                    "--per-rule-ignores",
                    "DEP002=accelerate|python-multipart|peft|protobuf|sentencepiece,"
                    "DEP004=plotly",
                ),
            ),
            root,
        ),
        Stage(
            "tests",
            (
                _uv(
                    "pytest",
                    "--cov-fail-under=100",
                    f"--cov-report=html:{coverage_report}",
                ),
            ),
            root,
        ),
        Stage(
            "property",
            (_uv("pytest", "tests/property", "-m", "property", "--no-cov", "-q"),),
            root,
        ),
        Stage(
            "acceptance",
            (
                _uv(
                    "pytest",
                    "tests/acceptance",
                    "-m",
                    "acceptance",
                    "--no-cov",
                    "-q",
                ),
            ),
            root,
        ),
        Stage(
            "architecture",
            (_uv("python", "scripts/check_architecture.py", "--package", "geoparser"),),
            root,
        ),
        Stage(
            "crap",
            (
                _uv(
                    "python",
                    "scripts/crap.py",
                    "--max-crap",
                    "5.99",
                    "--data-file",
                    str(coverage_data),
                ),
            ),
            root,
        ),
    ]

    if not skip_mutation:
        stages.append(
            Stage(
                "mutation",
                (
                    _uv("mutmut", "run"),
                    _uv("mutmut", "export-cicd-stats"),
                    _uv(
                        "python",
                        "scripts/mutation_gate.py",
                        "--max-survivors",
                        "0",
                        "--stats",
                        "mutants/mutmut-cicd-stats.json",
                    ),
                ),
                root,
            )
        )

    smoke_commands: list[Command] = [
        (
            "uv",
            "build",
            "--out-dir",
            str(artifact_dir / "dist"),
        ),
        _uv(
            "mkdocs",
            "build",
            "--strict",
            "--site-dir",
            str(artifact_dir / "site"),
        ),
    ]
    if not skip_docker:
        smoke_commands.extend(
            (
                (
                    "docker",
                    "build",
                    "--file",
                    "Dockerfile",
                    "--tag",
                    docker_tag,
                    ".",
                ),
                ("docker", "run", "--rm", docker_tag),
            )
        )
    stages.extend(
        [
            Stage("smoke", tuple(smoke_commands), root),
            Stage("diff-review", (("git", "diff", "--check"),), root),
        ]
    )
    return stages


def cleanup_docker_image(root: Path, env: dict[str, str], docker_tag: str) -> None:
    """Remove the exact temporary image used by a local smoke test."""
    subprocess.run(
        ("docker", "image", "rm", docker_tag),
        cwd=root,
        env=env,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def run_stages(stages: list[Stage], env: dict[str, str]) -> int:
    """Run stages in order and return the first failing command's status."""
    for stage in stages:
        print(f"\n== {stage.name} ==", flush=True)
        for command in stage.commands:
            result = subprocess.run(command, cwd=stage.cwd, env=env, check=False)
            if result.returncode:
                print(
                    f"Stage {stage.name!r} failed with exit code {result.returncode}.",
                    flush=True,
                )
                return result.returncode
    print("\nQuality gauntlet passed.", flush=True)
    return 0


@contextmanager
def _mutation_output_link(root: Path, artifact_dir: Path) -> Iterator[None]:
    """Keep mutmut's fixed output directory outside the checkout when possible."""
    repository_output = root / "mutants"
    if repository_output.exists() or repository_output.is_symlink():
        yield
        return

    external_output = artifact_dir / "mutants"
    external_output.mkdir(parents=True, exist_ok=True)
    repository_output.symlink_to(external_output, target_is_directory=True)
    try:
        yield
    finally:
        repository_output.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    """Run all quality stages unless an explicitly diagnostic flag is used."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-mutation",
        action="store_true",
        help="Skip mutation testing for local diagnosis; CI must not use this.",
    )
    parser.add_argument(
        "--skip-docker",
        action="store_true",
        help="Skip Docker commands for local diagnosis; CI must not use this.",
    )
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="geoparser-qa-") as directory:
        artifact_dir = Path(directory)
        docker_tag = f"geoparser:qa-{artifact_dir.name}"
        environment = os.environ.copy()
        environment.update(
            {
                "GEOPARSER_QA_ARTIFACT_DIR": str(artifact_dir),
                "TMPDIR": str(artifact_dir),
                "SQLITE_TMPDIR": str(artifact_dir),
                "COVERAGE_FILE": str(artifact_dir / ".coverage"),
            }
        )
        stages = build_stages(
            root,
            artifact_dir,
            skip_mutation=args.skip_mutation,
            skip_docker=args.skip_docker,
            docker_tag=docker_tag,
        )
        try:
            with _mutation_output_link(root, artifact_dir):
                return run_stages(stages, environment)
        finally:
            if not args.skip_docker:
                cleanup_docker_image(root, environment, docker_tag)


if __name__ == "__main__":
    raise SystemExit(main())
