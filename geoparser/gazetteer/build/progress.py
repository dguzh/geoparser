"""
Console output helpers for the gazetteer build pipeline.

Build activity is grouped by pipeline stage (acquire, stage, project, emit,
finalize), mirroring how the old installer grouped progress by source: each
stage owns a persistent bar that reads "<verb>ing ..." while it runs and
"<verb>ed ..." once every item in it has completed, turning from cyan to
green. Individual items within a stage (a download, a staged input, a
projected feature type, ...) render as dimmed, indented bars nested under
their stage and disappear as soon as they finish, so only the stage bars and
the currently active item remain on screen. There are no checkmarks and no
byte counts for downloads; progress within an item is shown as a percentage
(or, for indeterminate work, an animated bar with no percentage).
"""

import typing as t
from contextlib import contextmanager
from contextvars import ContextVar

from rich.console import Console
from rich.progress import BarColumn, Progress, ProgressColumn, Task, TimeElapsedColumn
from rich.rule import Rule
from rich.spinner import Spinner
from rich.table import Column, Table
from rich.text import Text

# Connector that visually nests an item (child) bar under its stage.
_CHILD_CONNECTOR = "  └─ "
_CHILD_SPINNER_NAME = "dots"

# Status colors. A stage is "in progress" (cyan) until all of its items
# complete, then "done" (green); item bars always use the in-progress color
# since they disappear on completion.
_RUNNING_STYLE = "cyan"
_DONE_STYLE = "green"

_console = Console(stderr=True)

# The Progress shared by every stage and item of the current build.
_active_progress: ContextVar[t.Optional[Progress]] = ContextVar(
    "active_build_progress", default=None
)
# The stage currently accepting items, so item() can attach without callers
# threading a stage object through unrelated modules (e.g. acquire.py).
_active_stage: ContextVar[t.Optional["Stage"]] = ContextVar(
    "active_build_stage", default=None
)


class _DescriptionColumn(ProgressColumn):
    """
    Render stage and item descriptions so the two are easy to tell apart.

    A stage task is shown as its running label in bold cyan while any of its
    items are outstanding, then its done label in bold green once complete.
    An item task is dimmed and nested under its stage with a tree connector
    and an animated spinner while it runs.
    """

    def __init__(self, width: int) -> None:
        super().__init__(
            table_column=Column(width=width, no_wrap=True, overflow="ellipsis")
        )
        self._child_spinner = Spinner(_CHILD_SPINNER_NAME, style="dim")

    def render(self, task: Task) -> Text:
        if task.fields.get("is_stage"):
            if task.finished:
                return Text(str(task.fields["done_label"]), style=f"bold {_DONE_STYLE}")
            return Text(str(task.description), style=f"bold {_RUNNING_STYLE}")
        line = Text(_CHILD_CONNECTOR, style="dim")
        line.append_text(self._child_spinner.render(task.get_time()))
        line.append(" ")
        line.append(str(task.description), style="dim")
        return line


class _ProgressReadoutColumn(ProgressColumn):
    """
    Render the progress readout for a task.

    A stage task is shown as a "completed/total" item count; an item task is
    shown as a percentage when it tracks a known quantity, or left blank for
    indeterminate work (its bar animates instead).
    """

    def render(self, task: Task) -> Text:
        if task.fields.get("is_stage"):
            total = int(task.total) if task.total else 0
            return Text(f"{int(task.completed)}/{total}", style="progress.percentage")
        if task.total:
            return Text(f"{int(task.percentage)}%", style="progress.percentage")
        return Text("")


class _StyledBarColumn(BarColumn):
    """
    Bar column colored by status: a stage bar turns from in-progress to done
    when all of its items complete, while item bars always use the
    in-progress color (they disappear on completion, before it would matter).
    """

    def render(self, task: Task):
        if task.fields.get("is_stage") and task.finished:
            style = _DONE_STYLE
        else:
            style = _RUNNING_STYLE
        self.complete_style = style
        self.finished_style = style
        return super().render(task)


def _layout_width() -> int:
    """Return the current terminal width."""
    return max(_console.size.width, 1)


def _description_width() -> int:
    """Return the description column width (half of the layout width)."""
    return max(_layout_width() // 2, 1)


def _make_progress() -> Progress:
    """Build a progress display with the shared column layout."""
    return Progress(
        _DescriptionColumn(_description_width()),
        _StyledBarColumn(),
        _ProgressReadoutColumn(),
        TimeElapsedColumn(),
        console=_console,
        expand=True,
    )


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
def build_display() -> t.Iterator[None]:
    """
    Open the shared live display for a build.

    Stages and items created within the ``with`` block attach to this
    display. Nesting is supported: an inner call reuses the already-active
    display.

    Yields:
        None
    """
    if _active_progress.get() is not None:
        yield
        return
    progress = _make_progress()
    token = _active_progress.set(progress)
    try:
        with progress:
            yield
    finally:
        _active_progress.reset(token)


class Stage:
    """
    A pipeline stage's progress: a persistent bar tracking completed items.

    Items are transient nested bars created with :func:`item`; they attach to
    whichever stage is currently active and disappear once finished. Callers
    advance the stage's own item count explicitly with :meth:`advance`, once
    per unit of work the stage represents (regardless of whether that unit
    displayed an item bar).
    """

    def __init__(self, running_label: str, done_label: str, total_items: int):
        self.running_label = running_label
        self.done_label = done_label
        self.total_items = total_items
        self._progress: t.Optional[Progress] = None
        self._owns_display = False
        self._task_id: t.Optional[int] = None
        self._stage_token = None

    def __enter__(self) -> "Stage":
        progress = _active_progress.get()
        if progress is None:
            progress = _make_progress()
            progress.start()
            self._owns_display = True
        self._progress = progress
        self._task_id = progress.add_task(
            self.running_label,
            total=self.total_items,
            is_stage=True,
            done_label=self.done_label,
        )
        self._stage_token = _active_stage.set(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        _active_stage.reset(self._stage_token)
        if exc_type is None:
            # Snap to completion so the bar turns green and the label flips
            # to its done form even if a caller under-counted advances.
            self._progress.update(self._task_id, completed=self.total_items)
        if self._owns_display:
            self._progress.stop()

    def advance(self, count: int = 1) -> None:
        """Mark ``count`` more items of this stage as completed."""
        self._progress.advance(self._task_id, count)

    def item(
        self, description: str, total: t.Optional[float] = None
    ) -> "_Item":
        """Create an item bar nested under this stage."""
        task_id = self._progress.add_task(description, total=total, is_child=True)
        return _Item(self._progress, task_id)


@contextmanager
def stage(running_label: str, done_label: str, total_items: int) -> t.Iterator[Stage]:
    """
    Open a stage's progress group.

    Args:
        running_label: Label shown while the stage has outstanding items
        done_label: Label shown once every item has completed
        total_items: Number of items the stage represents

    Yields:
        The active :class:`Stage`
    """
    group = Stage(running_label, done_label, total_items)
    with group:
        yield group


class _Item:
    """A transient, nested progress bar for one unit of work within a stage."""

    def __init__(self, progress: Progress, task_id: int):
        self._progress = progress
        self._task_id = task_id

    def __enter__(self) -> "_Item":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._progress.remove_task(self._task_id)

    def update(self, advance: float) -> None:
        """Advance this item's progress by ``advance`` units."""
        self._progress.update(self._task_id, advance=advance)


@contextmanager
def item(description: str, total: t.Optional[float] = None) -> t.Iterator[_Item]:
    """
    Display a nested, transient progress item.

    Attaches under the currently active stage (see :func:`stage`) so it nests
    and disappears the way the stage's own items do. Outside of an active
    stage it manages a standalone display, indeterminate by default.

    Args:
        description: Human-readable description of the item
        total: Known quantity of work, if any (renders a percentage); ``None``
            renders an animated, indeterminate bar

    Yields:
        The active item bar
    """
    active_stage = _active_stage.get()
    if active_stage is not None:
        bar = active_stage.item(description, total)
        try:
            yield bar
        finally:
            bar.__exit__(None, None, None)
        return

    progress = _active_progress.get()
    owns_display = progress is None
    if owns_display:
        progress = _make_progress()
        progress.start()
    task_id = progress.add_task(description, total=total, is_child=True)
    try:
        yield _Item(progress, task_id)
    finally:
        progress.remove_task(task_id)
        if owns_display:
            progress.stop()


def advance(count: int = 1) -> None:
    """
    Advance the currently active stage's item count, if any.

    Lets modules record completed work (see :mod:`acquire`) without holding a
    reference to the stage object.

    Args:
        count: Number of items to mark as completed
    """
    active_stage = _active_stage.get()
    if active_stage is not None:
        active_stage.advance(count)
