from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator, List, Optional

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    ProgressColumn,
    Task,
    TimeElapsedColumn,
)
from rich.rule import Rule
from rich.spinner import Spinner
from rich.table import Column, Table
from rich.text import Text

# Connector that visually nests an action (child) bar under its source.
_CHILD_CONNECTOR = "  └─ "
_CHILD_SPINNER_NAME = "dots"

# Labels for the source (parent) line. Past tense once all steps complete so
# each state reads naturally without symbols.
_SOURCE_PROCESSING_LABEL = "Processing "
_SOURCE_PROCESSED_LABEL = "Processed "
# Status colors. A source is "in progress" (cyan) until all of its steps
# complete, then "done" (green); action bars use the in-progress color.
_RUNNING_STYLE = "cyan"
_DONE_STYLE = "green"

# Holds the progress group of the source currently being installed. Progress
# bars created deep inside the pipeline stages read this to attach themselves
# to the shared, per-source display instead of creating their own.
_active_group: ContextVar[Optional["_SourceProgress"]] = ContextVar(
    "active_progress_group", default=None
)


class _DescriptionColumn(ProgressColumn):
    """
    Render the description so sources and actions are easy to tell apart.

    A source (parent) task is shown as "Processing <name>" while its pipeline
    runs, then "Processed <name>" once all steps complete. An action (child)
    task is dimmed and nested under its source with a tree connector and an
    animated spinner while the step is running.
    """

    def __init__(self, description_width: int) -> None:
        super().__init__(
            table_column=Column(
                width=description_width, no_wrap=True, overflow="ellipsis"
            )
        )
        self._child_spinner = Spinner(_CHILD_SPINNER_NAME, style="dim")

    def render(self, task: Task) -> Text:
        description = str(task.description)
        if task.fields.get("is_step_task"):
            if task.finished:
                return Text.assemble(
                    (_SOURCE_PROCESSED_LABEL, _DONE_STYLE),
                    (description, "bold"),
                )
            return Text.assemble(
                (_SOURCE_PROCESSING_LABEL, _RUNNING_STYLE),
                (description, "bold"),
            )
        if task.fields.get("is_child"):
            line = Text(_CHILD_CONNECTOR, style="dim")
            if not task.finished:
                line.append_text(self._child_spinner.render(task.get_time()))
                line.append(" ")
            line.append(description, style="dim")
            return line
        return Text(description)


class _StepAwareColumn(ProgressColumn):
    """
    Render the absolute-progress readout for a task.

    The per-source step (parent) task is shown as a "completed/total" step
    count; ordinary task bars are shown as a percentage.
    """

    def render(self, task: Task) -> Text:
        if task.fields.get("is_step_task"):
            total = int(task.total) if task.total else 0
            return Text(f"{int(task.completed)}/{total}", style="progress.percentage")
        return Text(f"{int(task.percentage)}%", style="progress.percentage")


class _StyledBarColumn(BarColumn):
    """
    Bar column that colors bars by status so the hierarchy and state are
    visible at a glance: a source bar turns from in-progress to done when all
    of its steps complete, while action bars use the in-progress color.
    """

    def render(self, task: Task):
        if task.fields.get("is_step_task") and task.finished:
            style = _DONE_STYLE
        else:
            style = _RUNNING_STYLE
        self.complete_style = style
        self.finished_style = style
        return super().render(task)


def _build_columns(description_width: int) -> List[ProgressColumn]:
    """
    Build the shared column layout used by every bar.

    Each bar shows a fixed-width description, the bar, a progress readout (a
    step count for the source task, a percentage otherwise) and the elapsed
    time. Source and action bars are styled differently so the hierarchy is
    obvious.
    """
    return [
        _DescriptionColumn(description_width),
        _StyledBarColumn(),
        _StepAwareColumn(),
        TimeElapsedColumn(),
    ]


def _console() -> Console:
    """Return the console used for installer headings, summaries and progress."""
    return Console(stderr=True)


def _layout_width(console: Optional[Console] = None) -> int:
    """
    Return the effective layout width for installer output.

    Uses the current terminal width from Rich's console (no hardcoded cap).
    """
    console = console or _console()
    return max(console.size.width, 1)


def _description_width(console: Optional[Console] = None) -> int:
    """Return the description column width (half of the layout width)."""
    return max(_layout_width(console) // 2, 1)


def _layout_console() -> Console:
    """Return a console constrained to the current layout width."""
    return Console(stderr=True, width=_layout_width(), soft_wrap=False)


def _create_progress(description_width: int, console: Console) -> Progress:
    """Create a :class:`Progress` instance with the shared column layout."""
    return Progress(
        *_build_columns(description_width),
        console=console,
        expand=True,
    )


class _RichProgressBar:
    """
    Context-managed progress bar backed by :class:`rich.progress.Progress`.

    When created inside an active source group it attaches to that group's
    shared display as a nested action (child) bar and removes itself on
    completion (so the group stays compact). Otherwise it owns a standalone
    display.

    Exposes the minimal interface used throughout the installer
    (``update(advance)`` plus the context-manager protocol).
    """

    def __init__(
        self,
        total: int,
        description: str,
        unit: str,
        progress: Optional[Progress] = None,
    ) -> None:
        self.total = total
        self.description = description
        self.unit = unit
        self._owns_progress = progress is None
        if progress is not None:
            self._progress = progress
        else:
            console = _layout_console()
            self._progress = _create_progress(_description_width(console), console)
        self._task_id = None

    def __enter__(self) -> "_RichProgressBar":
        if self._owns_progress:
            self._progress.start()
        # Grouped bars are flagged as children so the display nests and styles
        # them under their source; standalone bars render plainly.
        self._task_id = self._progress.add_task(
            self.description, total=self.total, is_child=not self._owns_progress
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._owns_progress:
            self._progress.stop()
        else:
            # Drop the finished child bar so only the source-level task and the
            # currently active step remain on screen.
            self._progress.remove_task(self._task_id)

    def update(self, advance: int) -> None:
        """Advance the progress bar by ``advance`` units."""
        self._progress.update(self._task_id, advance=advance)


class _SourceProgress:
    """
    Shared progress display for a single source's pipeline run.

    Holds one :class:`rich.progress.Progress` with a persistent parent task
    that tracks completed pipeline steps. Child bars created within the group
    attach to the same display.
    """

    def __init__(self, description: str, total_steps: int) -> None:
        self.description = description
        self.total_steps = total_steps
        self._console = _layout_console()
        self._progress = _create_progress(
            _description_width(self._console), self._console
        )
        self._step_task_id = None

    def __enter__(self) -> "_SourceProgress":
        self._progress.start()
        self._step_task_id = self._progress.add_task(
            self.description, total=self.total_steps, is_step_task=True
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._progress.stop()

    def advance_step(self) -> None:
        """Mark one pipeline step as completed."""
        self._progress.advance(self._step_task_id, 1)

    def create_bar(self, total: int, description: str, unit: str) -> _RichProgressBar:
        """Create a child bar attached to this group's shared display."""
        return _RichProgressBar(total, description, unit, progress=self._progress)


@contextmanager
def source_progress(description: str, total_steps: int) -> Iterator[_SourceProgress]:
    """
    Open a shared progress group for a source's pipeline run.

    A persistent parent bar tracks completed pipeline steps. Progress bars
    created within the ``with`` block (via :func:`create_progress_bar`) attach
    to the same display as transient child bars.

    Args:
        description: Label for the source-level (parent) bar
        total_steps: Total number of pipeline steps for the source

    Yields:
        The active :class:`_SourceProgress` group
    """
    group = _SourceProgress(str(description), total_steps)
    token = _active_group.set(group)
    try:
        with group:
            yield group
    finally:
        _active_group.reset(token)


def create_progress_bar(
    total: int,
    description: str,
    unit: str = "items",
) -> _RichProgressBar:
    """
    Create a standardized progress bar for installation operations.

    This function ensures consistent progress bar formatting across all
    installation stages. When called within an active :func:`source_progress`
    group, the bar attaches to that group's shared display; otherwise it owns a
    standalone display.

    Args:
        total: Total number of items to process
        description: Description of the operation
        unit: Unit name for items being processed

    Returns:
        A configured rich-backed progress bar
    """
    group = _active_group.get()
    if group is not None:
        return group.create_bar(total, description, unit)
    return _RichProgressBar(total=total, description=description, unit=unit)


def print_gazetteer_header(gazetteer_name: str) -> None:
    """
    Print a heading before gazetteer installation begins.

    Args:
        gazetteer_name: Name of the gazetteer being installed
    """
    console = _console()
    width = _layout_width(console)
    console.print()
    console.print(Rule(gazetteer_name, style="bold"), width=width)
    console.print()


def print_gazetteer_summary(feature_count: int, name_count: int) -> None:
    """
    Print a short summary after gazetteer installation completes.

    Args:
        feature_count: Number of features registered for the gazetteer
        name_count: Number of names registered for the gazetteer
    """
    console = _console()
    width = _layout_width(console)
    table = Table(show_header=False, box=None, pad_edge=False)
    table.add_column(style="dim")
    table.add_column(justify="right")

    table.add_row("Features", f"{feature_count:,}")
    table.add_row("Names", f"{name_count:,}")

    console.print()
    console.print()
    console.print("Summary", style="bold", width=width)
    console.print()
    console.print(table, width=width)
    console.print()
