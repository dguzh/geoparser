import json
import sys
from types import SimpleNamespace
from typing import Any

from scripts import mutation_gate


def _stats_path(tmp_path, *, survived: int) -> str:
    path = tmp_path / "mutmut-cicd-stats.json"
    path.write_text(
        json.dumps({"killed": 10, "survived": survived, "total": 10 + survived}),
        encoding="utf-8",
    )
    return str(path)


def test_mutation_gate_prints_actionable_mutant_diagnostics(
    monkeypatch: Any, tmp_path, capsys: Any
) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_run(command, *, check, capture_output, text):
        calls.append(tuple(command))
        return SimpleNamespace(
            returncode=0,
            stdout=(
                "    mutant_1: survived\n    mutant_2: timeout\n    mutant_3: killed\n"
            ),
            stderr="",
        )

    monkeypatch.setattr(mutation_gate.subprocess, "run", fake_run)

    result = mutation_gate.main(
        ["--max-survivors", "0", "--stats", _stats_path(tmp_path, survived=2)]
    )

    assert result == 1
    assert calls == [(sys.executable, "-m", "mutmut", "results")]
    error = capsys.readouterr().err
    assert "mutant_1: survived" in error
    assert "mutant_2: timeout" in error
    assert "mutant_3: killed" not in error


def test_mutation_gate_reports_unavailable_mutant_diagnostics(
    monkeypatch: Any, tmp_path, capsys: Any
) -> None:
    def fake_run(command, *, check, capture_output, text):
        return SimpleNamespace(returncode=127, stdout="", stderr="mutmut missing")

    monkeypatch.setattr(mutation_gate.subprocess, "run", fake_run)

    result = mutation_gate.main(
        ["--max-survivors", "0", "--stats", _stats_path(tmp_path, survived=1)]
    )

    assert result == 1
    assert (
        "mutmut results failed with exit code 127: mutmut missing"
        in capsys.readouterr().err
    )
