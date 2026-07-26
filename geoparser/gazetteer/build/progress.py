"""
Console output helpers for the gazetteer build pipeline.

Build activity is grouped by pipeline stage (preparing sources, compiling
features, building the artifact; see :mod:`builder`), mirroring how the old
installer grouped progress by source: each stage owns a persistent bar that
reads "<verb>ing ..." while it runs and "<verb>ed ..." once every item in it
has completed, turning from cyan to green. Individual items within a stage (a
download, a staged source, a query run against a feature block, ...) render
as dimmed, indented bars nested under their stage and disappear as soon as
they finish, so only the stage bars and the currently active item remain on
screen. There are no checkmarks and no byte counts for downloads; progress
within an item is shown as a percentage (or, for indeterminate work, an
animated bar with no percentage). A determinate item that finishes
successfully is snapped to 100% and held there briefly (see
:data:`_COMPLETION_PAUSE_SECONDS`) before it disappears, so it visibly
completes rather than seeming to vanish mid-step, whether it was polling
normally or sitting at some percentage right up to the end. A failed item
disappears immediately instead, since there is no completed state to show.

Every item that appears leaves a mark on its stage: the stage advances by one
the moment its item disappears, so the stage's own percentage always
reflects real, finished work rather than jumping only once several items
have quietly come and gone. A stage's ``total_items`` is a best
estimate (the exact number of items some units of work will show, e.g. an
acquisition's download-then-extract, is only known once it runs); the count
grows on the fly if advances outrun it, so the displayed total never falls
behind reality, and is snapped to match whatever actually completed once the
stage exits.

Database operations (a single DuckDB query, or a batch of SQLite statements)
report a percentage too, using :func:`track`, which runs the operation on a
background thread while polling a caller-supplied progress function (for
DuckDB, ``connection.query_progress()``; for known-size batches, the fraction
of rows or statements completed so far). These are estimates: DuckDB does not
track progress for every query shape, and statement-count progress does not
account for statements taking unequal time, but they give a useful sense of
motion for otherwise silent, long-running steps. Their items are always
created determinate (``total=100``) so they read "0%" immediately rather than
ever showing an animated, indeterminate bar, even briefly. Each individual
query gets its own item, shown and disposed of in turn, rather than several
queries sharing one bar (which would either not reflect their real, separate
progress or require guessing at how to divide the bar between them).
"""

import threading
import time
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

# How long a completed item lingers at 100% before disappearing. Without
# this, an item that jumps straight from 0% (or wherever it was polling) to
# done in the same instant it finishes never actually renders its completed
# state, making the step look like it vanished rather than finished.
_COMPLETION_PAUSE_SECONDS = 0.15

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

    Both a stage and an item read as a plain percentage when their progress
    is known, or left blank for indeterminate work (its bar animates
    instead); showing the same "NN%" form for both keeps the display
    consistent rather than mixing a raw item count into an otherwise
    percentage-based display. The column has a fixed, narrow width so this
    text changing length (e.g. "9%" to "100%", or one row disappearing while
    another remains) never shifts every other column alongside it. The width
    is sized to the widest reading ("100%"), so right-aligned text fills it
    at that width with no slack, giving the same one-space gap on both sides
    (to the bar on the left, to the elapsed time on the right); narrower
    readings still lean right and open up a larger gap on the left only.
    """

    def __init__(self) -> None:
        super().__init__(
            table_column=Column(width=4, justify="right", no_wrap=True)
        )

    def render(self, task: Task) -> Text:
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
    for every item bar that appeared and finished, so nothing disappears
    without leaving a mark on the stage it belongs to. ``total_items`` is
    only an initial estimate: it grows automatically if advances outrun it,
    so the displayed total is never less than what has actually completed.
    """

    def __init__(self, running_label: str, done_label: str, total_items: int):
        self.running_label = running_label
        self.done_label = done_label
        self.total_items = total_items
        self._completed = 0
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
        """
        Mark ``count`` more items of this stage as completed.

        Grows ``total_items`` first if this would otherwise complete more
        items than the stage's estimate accounted for, so the bar never
        shows more completed than total and never has to jump backwards.
        """
        self._completed += count
        if self._completed > self.total_items:
            self.total_items = self._completed
            self._progress.update(self._task_id, total=self.total_items)
        self._progress.advance(self._task_id, count)

    def item(
        self, description: str, total: t.Optional[float] = None
    ) -> "_Item":
        """Create an item bar nested under this stage."""
        task_id = self._progress.add_task(description, total=total, is_child=True)
        return _Item(self._progress, task_id, total=total)


@contextmanager
def stage(running_label: str, done_label: str, total_items: int) -> t.Iterator[Stage]:
    """
    Open a stage's progress group.

    Args:
        running_label: Label shown while the stage has outstanding items
        done_label: Label shown once every item has completed
        total_items: Estimated number of items the stage represents; grows
            automatically (see :meth:`Stage.advance`) if more complete

    Yields:
        The active :class:`Stage`
    """
    group = Stage(running_label, done_label, total_items)
    with group:
        yield group


class _Item:
    """A transient, nested progress bar for one unit of work within a stage."""

    def __init__(
        self,
        progress: Progress,
        task_id: int,
        total: t.Optional[float] = None,
    ):
        self._progress = progress
        self._task_id = task_id
        self._determinate = total is not None
        self._total = total

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
            self._total = 100
        self._progress.update(self._task_id, completed=percent)

    def close(self, success: bool = True) -> None:
        """
        Finish this item and remove its bar.

        On success, a determinate item is first snapped to its full total
        (in case the caller under-reported the very last step) and briefly
        held on screen so its completed state is actually visible, rather
        than disappearing in the same instant it reaches 100% (see
        :data:`_COMPLETION_PAUSE_SECONDS`). A failed item disappears at once;
        there is nothing meaningful to show.

        Args:
            success: Whether the work this item tracked finished without error
        """
        if success and self._determinate and self._total:
            self._progress.update(self._task_id, completed=self._total)
            self._progress.refresh()
            time.sleep(_COMPLETION_PAUSE_SECONDS)
        self._progress.remove_task(self._task_id)


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
        success = False
        try:
            yield bar
            success = True
        finally:
            bar.close(success=success)
        return

    progress = _active_progress.get()
    owns_display = progress is None
    if owns_display:
        progress = _make_progress()
        progress.start()
    task_id = progress.add_task(description, total=total, is_child=True)
    bar = _Item(progress, task_id, total=total)
    success = False
    try:
        yield bar
        success = True
    finally:
        bar.close(success=success)
        if owns_display:
            progress.stop()


def track(
    bar: _Item,
    poll: t.Callable[[], t.Optional[float]],
    run: t.Callable[[], None],
    poll_interval: float = 0.1,
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
    finishes successfully, ``bar`` is snapped to 100% regardless of the last
    polled value, since DuckDB's estimate can undershoot right up to the end.

    A caller with several queries to run should give each its own item and
    ``track()`` call in turn, rather than share one bar between them: that
    way every bar's progress is real, and the display simply shows one
    finishing before the next appears.

    Args:
        bar: The item bar to update; should be created with ``total=100``
        poll: Returns the current progress percentage, or a negative
            number/``None`` while not yet known
        run: The work to perform; exceptions are re-raised on the calling
            thread once it returns
        poll_interval: Seconds between polls

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
    bar.set_progress(100)


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


def label_suffixes(labels: t.Sequence[str]) -> t.List[str]:
    """
    Number labels that repeat, so identical-looking items are told apart.

    Several items in a row can legitimately share a base description (e.g.
    one "Collecting names from X" per configured name, or one "Assembling
    features from X" per feature block that happens to share a source). Left
    unnumbered, a repeat looks like the previous item's bar restarted rather
    than a new, distinct one appearing; this returns a same-length list of
    suffixes to append to each label; ``""`` for labels that occur only once,
    or ``" (i/N)"`` (1-based, in order of appearance) for each occurrence of
    one that repeats.

    Args:
        labels: Base descriptions, in the order their items will be shown

    Returns:
        Suffix to append to each label at the same position

    Example:
        >>> label_suffixes(["Loading A", "Collecting names from A", "Collecting names from A"])
        ['', ' (1/2)', ' (2/2)']
    """
    totals: t.Dict[str, int] = {}
    for label in labels:
        totals[label] = totals.get(label, 0) + 1
    seen: t.Dict[str, int] = {}
    suffixes = []
    for label in labels:
        total = totals[label]
        if total <= 1:
            suffixes.append("")
            continue
        seen[label] = seen.get(label, 0) + 1
        suffixes.append(f" ({seen[label]}/{total})")
    return suffixes
