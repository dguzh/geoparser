"""
Unit tests for geoparser/gazetteer/build/progress.py

Exercises the progress-display building blocks directly: the custom
columns, stage/item lifecycle, standalone (non-nested) display paths, and
the polling helpers used by :func:`track`.
"""

import pytest

from geoparser.gazetteer.build import progress as progress_module
from geoparser.gazetteer.build.progress import (
    Stage,
    _ProgressReadoutColumn,
    _sample,
    advance,
    build_display,
    item,
    label_suffixes,
    stage,
)


@pytest.mark.unit
class TestProgressReadoutColumn:
    """Test the percentage readout column."""

    def test_renders_blank_for_indeterminate_task(self):
        """An indeterminate task (total=None) renders no percentage text."""
        progress = progress_module._make_progress()
        task_id = progress.add_task("Working", total=None)
        task = progress.tasks[0]
        assert task_id == task.id

        rendered = _ProgressReadoutColumn().render(task)

        assert str(rendered) == ""

    def test_renders_percentage_for_determinate_task(self):
        """A determinate task renders its percentage."""
        progress = progress_module._make_progress()
        progress.add_task("Working", total=100, completed=42)
        task = progress.tasks[0]

        rendered = _ProgressReadoutColumn().render(task)

        assert str(rendered) == "42%"


@pytest.mark.unit
class TestBuildDisplay:
    """Test the build_display() context manager."""

    def test_nested_call_reuses_active_display(self):
        """A nested build_display() call is a no-op, reusing the outer one."""
        with build_display():
            outer_progress = progress_module._active_progress.get()
            assert outer_progress is not None
            with build_display():
                assert progress_module._active_progress.get() is outer_progress
            # Still active after the inner (reused) context exits.
            assert progress_module._active_progress.get() is outer_progress
        assert progress_module._active_progress.get() is None


@pytest.mark.unit
class TestStageStandalone:
    """Test Stage used without an enclosing build_display()."""

    def test_owns_and_stops_its_own_display(self):
        """A stage opened outside build_display() creates its own display."""
        assert progress_module._active_progress.get() is None

        with Stage("Running", "Done", 1) as group:
            assert group._owns_display is True
            assert group._progress is not None

        # The stage's own progress display was stopped and did not leak into
        # the module-level active progress context.
        assert progress_module._active_progress.get() is None

    def test_nested_inside_build_display_does_not_own_display(self):
        """A stage inside build_display() reuses the shared display."""
        with build_display():
            with Stage("Running", "Done", 1) as group:
                assert group._owns_display is False

    def test_advance_grows_total_items_beyond_estimate(self):
        """Advancing past the initial estimate grows total_items instead of
        overflowing past 100%."""
        with Stage("Running", "Done", 1) as group:
            group.advance(1)
            assert group.total_items == 1
            group.advance(1)
            assert group.total_items == 2
            assert group._completed == 2


@pytest.mark.unit
class TestItemLifecycle:
    """Test the _Item bar returned by item()/Stage.item()."""

    def test_update_advances_progress(self):
        """update() advances the item's completed amount."""
        with Stage("Running", "Done", 1):
            with item("Working", total=100) as bar:
                bar.update(30)
                task = bar._progress.tasks[bar._task_id]
                assert task.completed == 30

    def test_set_progress_switches_indeterminate_to_determinate(self):
        """set_progress() on an indeterminate item makes it determinate."""
        with Stage("Running", "Done", 1):
            with item("Working") as bar:
                assert bar._determinate is False
                bar.set_progress(55)
                assert bar._determinate is True
                assert bar._total == 100
                task = bar._progress.tasks[bar._task_id]
                assert task.completed == 55

    def test_standalone_item_without_active_stage_or_display(self):
        """item() outside any stage or display manages its own display."""
        assert progress_module._active_progress.get() is None
        assert progress_module._active_stage.get() is None

        with item("Working", total=100) as bar:
            bar.set_progress(50)

        assert progress_module._active_progress.get() is None

    def test_standalone_item_reuses_active_display_without_stage(self):
        """item() inside build_display() but without an active stage still
        attaches to the shared display rather than creating its own."""
        with build_display():
            with item("Working", total=100) as bar:
                assert bar._progress is progress_module._active_progress.get()

    def test_advance_without_active_stage_is_a_no_op(self):
        """advance() is safe to call with no active stage."""
        assert progress_module._active_stage.get() is None

        advance()  # Should not raise


@pytest.mark.unit
class TestSample:
    """Test the _sample() polling helper."""

    def test_ignores_poll_errors(self):
        """A poll() that raises is swallowed, leaving the bar untouched."""
        with Stage("Running", "Done", 1):
            with item("Working", total=100) as bar:

                def _failing_poll():
                    raise RuntimeError("boom")

                _sample(bar, _failing_poll)

                task = bar._progress.tasks[bar._task_id]
                assert task.completed == 0

    def test_ignores_negative_and_none_readings(self):
        """Negative or missing readings leave the bar's progress unchanged."""
        with Stage("Running", "Done", 1):
            with item("Working", total=100) as bar:
                _sample(bar, lambda: -1)
                _sample(bar, lambda: None)

                task = bar._progress.tasks[bar._task_id]
                assert task.completed == 0

    def test_applies_valid_readings(self):
        """A valid non-negative reading updates the bar's progress."""
        with Stage("Running", "Done", 1):
            with item("Working", total=100) as bar:
                _sample(bar, lambda: 77)

                task = bar._progress.tasks[bar._task_id]
                assert task.completed == 77


@pytest.mark.unit
class TestLabelSuffixes:
    """Test the label_suffixes() helper."""

    def test_unique_labels_get_no_suffix(self):
        """Labels that occur once are returned unsuffixed."""
        assert label_suffixes(["Reading A", "Reading B"]) == ["", ""]

    def test_repeated_labels_are_numbered_in_order(self):
        """Repeated labels are numbered in order of appearance."""
        labels = ["Reading A", "Collecting names from A", "Collecting names from A"]

        assert label_suffixes(labels) == ["", " (1/2)", " (2/2)"]

    def test_empty_input_returns_empty_list(self):
        """An empty label list returns an empty suffix list."""
        assert label_suffixes([]) == []


@pytest.mark.unit
class TestStageContextManagerFunction:
    """Test the stage() context manager function."""

    def test_yields_a_stage_instance(self):
        """stage() yields the Stage it created."""
        with stage("Running", "Done", 1) as group:
            assert isinstance(group, Stage)
            assert group.running_label == "Running"
            assert group.done_label == "Done"
