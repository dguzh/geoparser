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


def _unaccounted_stats_path(tmp_path, **counts: int) -> str:
    """A stats file whose totals need not add up, for the accounting checks."""
    path = tmp_path / "mutmut-cicd-stats.json"
    path.write_text(json.dumps(counts), encoding="utf-8")
    return str(path)


def test_mutation_gate_fails_when_the_run_checked_nothing(
    tmp_path, capsys: Any
) -> None:
    """
    A run that generated mutants but checked none of them is not a pass.

    mutmut exits zero and writes a stats file even when its own baseline test
    run failed, leaving every mutant "not checked". Reading only the survivor
    count then reports a clean sheet for a gate that verified nothing at all,
    which is the most dangerous way for this check to be wrong.
    """
    result = mutation_gate.main(
        [
            "--max-survivors",
            "0",
            "--stats",
            _unaccounted_stats_path(tmp_path, killed=0, survived=0, total=2028),
        ]
    )

    assert result == 1
    assert "2028" in capsys.readouterr().err


def test_mutation_gate_fails_when_some_mutants_were_never_checked(
    tmp_path, capsys: Any
) -> None:
    """A partially completed run is reported rather than silently accepted."""
    result = mutation_gate.main(
        [
            "--max-survivors",
            "0",
            "--stats",
            _unaccounted_stats_path(
                tmp_path, killed=900, survived=0, no_tests=100, total=2028
            ),
        ]
    )

    assert result == 1
    assert "1028" in capsys.readouterr().err


def test_mutation_gate_accepts_a_run_that_accounts_for_every_mutant(
    tmp_path, capsys: Any
) -> None:
    """Every outcome category counts towards the accounting, not just kills."""
    result = mutation_gate.main(
        [
            "--max-survivors",
            "0",
            "--stats",
            _unaccounted_stats_path(
                tmp_path,
                killed=1812,
                survived=0,
                timeout=3,
                no_tests=212,
                total=2027,
            ),
        ]
    )

    assert result == 0
