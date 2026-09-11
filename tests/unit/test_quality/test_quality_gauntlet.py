from pathlib import Path

from scripts.quality_gauntlet import (
    build_stages,
    cleanup_docker_image,
    main,
    run_stages,
)


def test_quality_stages_have_the_required_order(tmp_path: Path) -> None:
    stages = build_stages(Path("/repo"), tmp_path)

    assert [stage.name for stage in stages] == [
        "baseline",
        "ruff",
        "ty",
        "dependencies",
        "tests",
        "property",
        "acceptance",
        "architecture",
        "crap",
        "mutation",
        "smoke",
        "diff-review",
    ]
    ty_command = next(stage for stage in stages if stage.name == "ty").commands[0]
    assert ty_command[-3:] == ("geoparser", "scripts", "tests")


def test_quality_stages_can_skip_expensive_local_checks(tmp_path: Path) -> None:
    stages = build_stages(Path("/repo"), tmp_path, skip_mutation=True, skip_docker=True)

    assert "mutation" not in {stage.name for stage in stages}
    smoke = next(stage for stage in stages if stage.name == "smoke")
    assert all(command[0] != "docker" for command in smoke.commands)


def test_quality_runner_uses_the_requested_ephemeral_docker_tag(tmp_path: Path) -> None:
    stages = build_stages(Path("/repo"), tmp_path, docker_tag="geoparser:test")
    smoke = next(stage for stage in stages if stage.name == "smoke")

    assert (
        "docker",
        "build",
        "--file",
        "Dockerfile",
        "--tag",
        "geoparser:test",
        ".",
    ) in smoke.commands
    assert ("docker", "run", "--rm", "geoparser:test") in smoke.commands


def test_quality_runner_removes_only_the_ephemeral_docker_image(
    monkeypatch, tmp_path: Path
) -> None:
    calls: list[tuple[tuple[str, ...], Path, dict[str, str], bool]] = []

    def fake_run(command, *, cwd, env, check, stdout, stderr):
        calls.append((tuple(command), cwd, env, check))
        return type("Completed", (), {"returncode": 0})()

    monkeypatch.setattr("scripts.quality_gauntlet.subprocess.run", fake_run)

    cleanup_docker_image(tmp_path, {"PATH": "test"}, "geoparser:test")

    assert calls == [
        (
            ("docker", "image", "rm", "geoparser:test"),
            tmp_path,
            {"PATH": "test"},
            False,
        )
    ]


def test_quality_runner_cleans_the_image_after_stages(monkeypatch) -> None:
    tags: list[str] = []

    monkeypatch.setattr("scripts.quality_gauntlet.run_stages", lambda stages, env: 0)
    monkeypatch.setattr(
        "scripts.quality_gauntlet.cleanup_docker_image",
        lambda root, env, docker_tag: tags.append(docker_tag),
    )

    assert main(["--skip-mutation"]) == 0
    assert len(tags) == 1
    assert tags[0].startswith("geoparser:qa-geoparser-qa-")


def test_quality_runner_stops_on_first_failed_command(
    monkeypatch, tmp_path: Path
) -> None:
    stages = build_stages(Path("/repo"), tmp_path)
    calls: list[tuple[tuple[str, ...], Path, dict[str, str]]] = []

    def fake_run(command, *, cwd, env, check):
        calls.append((tuple(command), cwd, env))
        return type("Completed", (), {"returncode": 17})()

    monkeypatch.setattr("scripts.quality_gauntlet.subprocess.run", fake_run)

    result = run_stages(stages, {"GEOPARSER_QA_ARTIFACT_DIR": str(tmp_path)})

    assert result == 17
    assert len(calls) == 1
    assert calls[0][0] == stages[0].commands[0]
    assert calls[0][1] == stages[0].cwd
    assert calls[0][2]["GEOPARSER_QA_ARTIFACT_DIR"] == str(tmp_path)


def test_quality_runner_preserves_stage_order_and_artifact_environment(
    monkeypatch, tmp_path: Path
) -> None:
    stages = build_stages(Path("/repo"), tmp_path)
    calls: list[tuple[str, str]] = []

    def fake_run(command, *, cwd, env, check):
        calls.append((command[0], env["GEOPARSER_QA_ARTIFACT_DIR"]))
        return type("Completed", (), {"returncode": 0})()

    monkeypatch.setattr("scripts.quality_gauntlet.subprocess.run", fake_run)

    result = run_stages(stages, {"GEOPARSER_QA_ARTIFACT_DIR": str(tmp_path)})

    assert result == 0
    assert len(calls) == sum(len(stage.commands) for stage in stages)
    assert all(artifact == str(tmp_path) for _, artifact in calls)
