"""
CRAP score gate.

CRAP (Change Risk Anti-Patterns) combines how branchy a function is with how
well it is tested::

    CRAP = complexity^2 * (1 - coverage)^3 + complexity

A fully covered function scores its own cyclomatic complexity, so the gate is
simultaneously a complexity ceiling for tested code and a much harsher one for
untested code. Run it after pytest has written a coverage data file.

    uv run python scripts/crap.py --max-crap 30

Exits non-zero when any measured function scores above the threshold.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from coverage import Coverage
from coverage.exceptions import NoSource
from radon.complexity import cc_visit

# Mirrors [tool.coverage.run] omit: the annotator is a server-rendered UI that
# the test suite does not measure, so it has no coverage to compute CRAP from.
DEFAULT_OMIT = ("geoparser/annotator",)


@dataclass(frozen=True)
class Score:
    """A single function's complexity, coverage and resulting CRAP score."""

    path: str
    name: str
    lineno: int
    complexity: int
    coverage: float

    @property
    def crap(self) -> float:
        """The CRAP score for this function."""
        uncovered = 1.0 - self.coverage
        return self.complexity**2 * uncovered**3 + self.complexity

    def __str__(self) -> str:
        return (
            f"{self.crap:7.2f}  cc={self.complexity:<3} "
            f"cov={self.coverage * 100:5.1f}%  {self.path}:{self.lineno} {self.name}"
        )


def _analyse(coverage: Coverage, path: Path) -> tuple[set[int], set[int]] | None:
    """
    Return the (statements, missing) line numbers for a file.

    Args:
        coverage: A loaded coverage session
        path: The file to analyse

    Returns:
        A tuple of statement and missing line numbers, or None when the file
        has no coverage data at all.
    """
    try:
        _, statements, _, missing, _ = coverage.analysis2(str(path))
    except NoSource:
        return None
    return set(statements), set(missing)


def score_file(coverage: Coverage, path: Path, root: Path) -> list[Score]:
    """
    Score every function and method in one source file.

    Args:
        coverage: A loaded coverage session
        path: The file to score
        root: Repository root, used to render relative paths

    Returns:
        One Score per function, ordered as they appear in the file.
    """
    analysed = _analyse(coverage, path)
    if analysed is None:
        return []
    statements, missing = analysed

    relative = path.relative_to(root).as_posix()
    scores = []
    for block in cc_visit(path.read_text(encoding="utf-8")):
        # cc_visit yields classes as well as functions; a class's own score is
        # the sum of its methods, which would double-count them.
        if block.letter == "C":
            continue
        span = range(block.lineno, block.endline + 1)
        owned = statements.intersection(span)
        # A function with no measurable statements (an overload stub, say)
        # cannot be under-tested, so it counts as fully covered.
        covered = 1.0
        if owned:
            covered = 1.0 - len(owned & missing) / len(owned)
        scores.append(
            Score(
                path=relative,
                name=block.fullname,
                lineno=block.lineno,
                complexity=block.complexity,
                coverage=covered,
            )
        )
    return scores


def collect(
    root: Path, package: Path, data_file: Path, omit: tuple[str, ...]
) -> list[Score]:
    """
    Score every function in the package.

    Args:
        root: Repository root
        package: Directory of the package to measure
        data_file: Path to the coverage data file written by pytest
        omit: Path prefixes, relative to root, to leave unmeasured

    Returns:
        Every function's Score, sorted worst first.
    """
    coverage = Coverage(data_file=str(data_file))
    coverage.load()

    scores: list[Score] = []
    for path in sorted(package.resolve().rglob("*.py")):
        relative = path.relative_to(root).as_posix()
        if any(relative.startswith(prefix) for prefix in omit):
            continue
        scores.extend(score_file(coverage, path, root))
    return sorted(scores, key=lambda score: score.crap, reverse=True)


def main(argv: list[str] | None = None) -> int:
    """
    Report the worst CRAP scores and fail if any breaches the threshold.

    Args:
        argv: Command line arguments, defaulting to sys.argv

    Returns:
        Process exit code: 0 when every function is within the threshold.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-crap", type=float, required=True)
    parser.add_argument("--data-file", type=Path, default=Path(".coverage"))
    parser.add_argument("--package", type=Path, default=Path("geoparser"))
    parser.add_argument("--top", type=int, default=15)
    parser.add_argument("--omit", nargs="*", default=list(DEFAULT_OMIT))
    args = parser.parse_args(argv)

    root = Path.cwd().resolve()
    if not args.data_file.exists():
        print(
            f"No coverage data at {args.data_file}; run pytest first.", file=sys.stderr
        )
        return 2

    scores = collect(root, args.package, args.data_file, tuple(args.omit))
    if not scores:
        print("No functions measured.", file=sys.stderr)
        return 2

    print(f"Worst {min(args.top, len(scores))} CRAP scores of {len(scores)} functions:")
    for score in scores[: args.top]:
        print(f"  {score}")

    breaches = [score for score in scores if score.crap > args.max_crap]
    if breaches:
        print(
            f"\n{len(breaches)} function(s) exceed the CRAP threshold "
            f"of {args.max_crap:g}:",
            file=sys.stderr,
        )
        for score in breaches:
            print(f"  {score}", file=sys.stderr)
        return 1

    print(
        f"\nAll {len(scores)} functions are within the CRAP threshold of {args.max_crap:g}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
