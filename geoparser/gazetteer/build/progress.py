"""
Console output helpers for the gazetteer build pipeline.
"""

import typing as t
from contextlib import contextmanager

from rich.console import Console
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TextColumn,
    TimeElapsedColumn,
)
from rich.rule import Rule
from rich.table import Table

_console = Console(stderr=True)


def print_build_header(gazetteer_name: str) -> None:
    """
    Print a heading before a gazetteer build begins.

    Args:
        gazetteer_name: Name of the gazetteer being built
    """
    _console.print()
    _console.print(Rule(gazetteer_name, style="bold"))
    _console.print()


def print_build_summary(feature_count: int, name_count: int) -> None:
    """
    Print a short summary after a gazetteer build completes.

    Args:
        feature_count: Number of features in the artifact
        name_count: Number of names in the artifact
    """
    table = Table(show_header=False, box=None, pad_edge=False)
    table.add_column(style="dim")
    table.add_column(justify="right")
    table.add_row("Features", f"{feature_count:,}")
    table.add_row("Names", f"{name_count:,}")

    _console.print()
    _console.print("Summary", style="bold")
    _console.print()
    _console.print(table)
    _console.print()


@contextmanager
def step(description: str) -> t.Iterator[None]:
    """
    Display a build step with a spinner while it runs.

    Args:
        description: Human-readable description of the step

    Yields:
        None
    """
    with _console.status(f"{description}..."):
        yield
    _console.print(f"[green]done[/green]  {description}")


class DownloadBar:
    """Context-managed byte progress bar for file downloads."""

    def __init__(self, total: int, description: str):
        self.total = total
        self.description = description
        self._progress = Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            DownloadColumn(),
            TimeElapsedColumn(),
            console=_console,
        )
        self._task_id = None

    def __enter__(self) -> "DownloadBar":
        self._progress.start()
        self._task_id = self._progress.add_task(self.description, total=self.total)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._progress.stop()

    def update(self, advance: int) -> None:
        """Advance the progress bar by ``advance`` bytes."""
        self._progress.update(self._task_id, advance=advance)
