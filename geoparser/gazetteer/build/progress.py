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

Database operations (a single DuckDB query, or a batch of SQLite statements)
report a percentage too, using :func:`track`, which runs the operation on a
background thread while polling a caller-supplied progress function (for
DuckDB, ``connection.query_progress()``; for known-size batches, the fraction
of rows or statements completed so far). These are estimates: DuckDB does not
track progress for every query shape, and statement-count progress does not
account for statements taking unequal time, but they give a useful sense of
motion for otherwise silent, long-running steps. Their items are always
created determinate (``total=100``) so they read "0%" immediately rather than
ever showing an animated, indeterminate bar, even briefly. When an item
covers several queries in sequence, :func:`scale_poll` and :func:`allocate`
give each query its own slice of the item's 0-100 range, so the bar only
ever climbs, never resetting to a lower number when the next query starts.
"""

import threading
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
    indeterminate work (its bar animates instead). The column has a fixed
    width so this text changing length (e.g. "9%" to "100%", or one row
    disappearing while another remains) never shifts every other column
    alongside it.
    """

    def __init__(self) -> None:
        super().__init__(
            table_column=Column(width=9, justify="right", no_wrap=True)
        )

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
        return _Item(self._progress, task_id, determinate=total is not None)


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

    def __init__(self, progress: Progress, task_id: int, determinate: bool = False):
        self._progress = progress
        self._task_id = task_id
        self._determinate = determinate

    def __enter__(self) -> "_Item":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._progress.remove_task(self._task_id)

    def update(self, advance: float) -> None:
        """Advance this item's progress by ``advance`` units."""
        self._progress.update(self._task_id, advance=advance)

    def set_progress(self, percent: float) -> None:
        """
        Set this item's progress to an absolute percentage (0-100).

        Callers that intend to report a percentage should create the item
        with ``total=100`` up front, so it reads "0%" immediately rather than
        flashing an animated, indeterminate bar before the first call. If it
        wasn't, this switches it from indeterminate to determinate on first
        use, as a fallback.
        """
        if not self._determinate:
            self._progress.update(self._task_id, total=100)
            self._determinate = True
        self._progress.update(self._task_id, completed=percent)


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
        yield _Item(progress, task_id, determinate=total is not None)
    finally:
        progress.remove_task(task_id)
        if owns_display:
            progress.stop()


def track(
    bar: _Item,
    poll: t.Callable[[], t.Optional[float]],
    run: t.Callable[[], None],
    poll_interval: float = 0.1,
    final: float = 100.0,
) -> None:
    """
    Run ``run()`` on a background thread while reporting live progress on ``bar``.

    ``poll()`` is called periodically (from this thread, so it must be safe to
    call concurrently with ``run()``) and should return a percentage in
    ``[0, 100]`` once known. Until the first such reading, ``poll()`` may
    return a negative number or ``None``; used for querying DuckDB's own query
    progress (``connection.query_progress()``), which reports -1 for queries it
    cannot track. ``bar`` should already be determinate (created with
    ``total=100``) so it reads "0%" rather than flashing an animated,
    indeterminate bar for the (possibly long) stretch before the first
    reading arrives, or at all if ``poll()`` never returns one. Once ``run()``
    finishes successfully, ``bar`` is snapped to ``final`` regardless of the
    last polled value, since DuckDB's estimate can undershoot right up to the
    end.

    When several operations run in sequence under the same ``bar`` (e.g. one
    item covering a query plus some follow-up queries), pass ``poll`` through
    :func:`scale_poll` and pick each operation's ``final`` from
    :func:`allocate`, so ``bar`` climbs across all of them instead of
    resetting to a low value every time a new operation starts polling from 0.

    Args:
        bar: The item bar to update; should be created with ``total=100``
        poll: Returns the current progress percentage, or a negative
            number/``None`` while not yet known
        run: The work to perform; exceptions are re-raised on the calling
            thread once it returns
        poll_interval: Seconds between polls
        final: Value ``bar`` is set to once ``run()`` finishes successfully

    Raises:
        Whatever exception ``run()`` raised, re-raised on the calling thread
    """
    error: t.List[BaseException] = []

    def _run() -> None:
        try:
            run()
        except BaseException as exc:  # noqa: BLE001 - re-raised below
            error.append(exc)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    while thread.is_alive():
        _sample(bar, poll)
        thread.join(timeout=poll_interval)
    thread.join()
    if error:
        raise error[0]
    bar.set_progress(final)


def scale_poll(
    poll: t.Callable[[], t.Optional[float]], start: float, end: float
) -> t.Callable[[], t.Optional[float]]:
    """
    Rescale a 0-100 progress function onto the sub-range ``[start, end)``.

    Used to let several sequential operations share one item bar without it
    ever moving backwards: each operation gets its own slice of the bar's
    overall range (see :func:`allocate`) and reports into that slice rather
    than the full 0-100 range.

    Args:
        poll: Progress function returning a percentage in ``[0, 100]``, or a
            negative number/``None`` while not yet known
        start: Start of the sub-range
        end: End of the sub-range

    Returns:
        A progress function whose readings fall within ``[start, end)``
    """

    def _scaled() -> t.Optional[float]:
        value = poll()
        if value is None or value < 0:
            return None
        return start + value / 100 * (end - start)

    return _scaled


def allocate(
    weights: t.Sequence[float], start: float = 0.0, end: float = 100.0
) -> t.List[t.Tuple[float, float]]:
    """
    Split ``[start, end)`` into consecutive sub-ranges proportional to ``weights``.

    Args:
        weights: Relative size of each sub-range; need not sum to anything in
            particular
        start: Start of the overall range
        end: End of the overall range

    Returns:
        One ``(sub_start, sub_end)`` pair per weight, in order, exactly
        covering ``[start, end)``
    """
    total = sum(weights) or 1.0
    span = end - start
    bounds = []
    cursor = start
    for weight in weights:
        next_cursor = cursor + span * (weight / total)
        bounds.append((cursor, next_cursor))
        cursor = next_cursor
    if bounds:
        # Floating-point drift could leave the last bound short of `end`.
        bounds[-1] = (bounds[-1][0], end)
    return bounds


def _sample(bar: _Item, poll: t.Callable[[], t.Optional[float]]) -> None:
    """Read one progress value and apply it to ``bar``, ignoring poll errors."""
    try:
        value = poll()
    except Exception:
        return
    if value is not None and value >= 0:
        bar.set_progress(value)


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
