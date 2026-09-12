"""
Mutation testing gate.

Reads the summary that ``mutmut export-cicd-stats`` writes and fails when more
mutants survived than the agreed baseline. A surviving mutant is a change to
the source that the test suite did not notice, so it marks a line that is
executed but not actually checked.

    uv run mutmut run
    uv run mutmut export-cicd-stats
    uv run python scripts/mutation_gate.py --max-survivors 0

Fix a survivor by strengthening the test that should have caught it, not by
raising the threshold.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

STATS_PATH = Path("mutants/mutmut-cicd-stats.json")


def summarize(stats: dict[str, int]) -> str:
    """
    Render a one-line summary of a mutation run.

    Args:
        stats: The counts mutmut exported

    Returns:
        A human-readable summary line
    """
    killed = stats.get("killed", 0)
    survived = stats.get("survived", 0)
    judged = killed + survived
    score = f"{100 * killed / judged:.1f}%" if judged else "n/a"
    return (
        f"score {score}  killed {killed}  survived {survived}  "
        f"timeout {stats.get('timeout', 0)}  suspicious {stats.get('suspicious', 0)}  "
        f"no tests {stats.get('no_tests', 0)}  skipped {stats.get('skipped', 0)}  "
        f"total {stats.get('total', 0)}"
    )


def mutation_diagnostics() -> str:
    """Return actionable non-killed mutant lines from the current run."""
    result = subprocess.run(
        (sys.executable, "-m", "mutmut", "results"),
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or "no output"
        return f"mutmut results failed with exit code {result.returncode}: {detail}"

    actionable_statuses = (
        ": survived",
        ": timeout",
        ": suspicious",
        ": segfault",
        ": caught by type check",
        ": check was interrupted by user",
    )
    return "\n".join(
        line
        for line in result.stdout.splitlines()
        if any(status in line for status in actionable_statuses)
    )


def main(argv: list[str] | None = None) -> int:
    """
    Report the mutation score and fail if too many mutants survived.

    Args:
        argv: Command line arguments, defaulting to sys.argv

    Returns:
        Process exit code: 0 when survivors are within the threshold.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-survivors", type=int, required=True)
    parser.add_argument("--stats", type=Path, default=STATS_PATH)
    args = parser.parse_args(argv)

    if not args.stats.exists():
        print(
            f"No mutation stats at {args.stats}; run "
            f"'mutmut run' then 'mutmut export-cicd-stats' first.",
            file=sys.stderr,
        )
        return 2

    stats = json.loads(args.stats.read_text(encoding="utf-8"))
    print(f"Mutation testing: {summarize(stats)}")

    survived = stats.get("survived", 0)
    if survived > args.max_survivors:
        diagnostics = mutation_diagnostics()
        print(
            f"\n{survived} mutant(s) survived, more than the agreed "
            f"{args.max_survivors}. Strengthen the tests that should have "
            f"killed them.",
            file=sys.stderr,
        )
        print(
            "\nMutation diagnostics:\n"
            + (diagnostics or "No actionable mutant details were returned."),
            file=sys.stderr,
        )
        return 1

    print(f"Within the agreed baseline of {args.max_survivors} surviving mutant(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
