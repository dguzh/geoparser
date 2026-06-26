"""
Unit tests for geoparser/gazetteer/installer/utils/progress.py

Tests the create_progress_bar utility function and the source_progress group.
"""

from unittest.mock import patch

import pytest
from rich.console import Console
from rich.progress import (
    DownloadColumn,
    MofNCompleteColumn,
    SpinnerColumn,
    TimeElapsedColumn,
    TransferSpeedColumn,
)

from geoparser.gazetteer.installer.utils.progress import (
    _CHILD_CONNECTOR,
    _SOURCE_PROCESSED_LABEL,
    _SOURCE_PROCESSING_LABEL,
    _description_width,
    _DescriptionColumn,
    _layout_width,
    _RichProgressBar,
    _StepAwareColumn,
    _StyledBarColumn,
    create_progress_bar,
    print_gazetteer_header,
    print_gazetteer_summary,
    source_progress,
)


@pytest.mark.unit
class TestCreateProgressBar:
    """Test create_progress_bar() function."""

    def test_creates_progress_bar_with_defaults(self):
        """Test creating progress bar with default unit."""
        # Act
        pbar = create_progress_bar(total=100, description="Processing")

        # Assert
        assert isinstance(pbar, _RichProgressBar)
        assert pbar.total == 100
        assert pbar.description == "Processing"
        assert pbar.unit == "items"

    def test_creates_progress_bar_with_custom_unit(self):
        """Test creating progress bar with custom unit."""
        # Act
        pbar = create_progress_bar(
            total=1000, description="Downloading", unit="records"
        )

        # Assert
        assert pbar.total == 1000
        assert pbar.description == "Downloading"
        assert pbar.unit == "records"

    def test_supports_context_manager_and_update(self):
        """Test the bar works as a context manager and advances on update."""
        # Act
        with create_progress_bar(total=10, description="Processing") as pbar:
            pbar.update(3)
            pbar.update(2)
            task = pbar._progress.tasks[0]

            # Assert
            assert task.completed == 5
            assert task.total == 10

    @pytest.mark.parametrize("unit", ["B", "bytes", "items", "rows", "view"])
    def test_layout_is_uniform_across_units(self, unit):
        """Test that the column layout is identical regardless of unit."""
        # Act
        pbar = create_progress_bar(total=100, description="Processing", unit=unit)
        column_types = [type(column) for column in pbar._progress.columns]

        # Assert
        assert column_types == [
            _DescriptionColumn,
            _StyledBarColumn,
            _StepAwareColumn,
            TimeElapsedColumn,
        ]

    @pytest.mark.parametrize("unit", ["B", "items"])
    def test_no_spinner_column(self, unit):
        """Test that the spinner column is no longer part of the layout."""
        # Act
        pbar = create_progress_bar(total=100, description="Processing", unit=unit)
        column_types = {type(column) for column in pbar._progress.columns}

        # Assert
        assert SpinnerColumn not in column_types

    @pytest.mark.parametrize("unit", ["B", "items"])
    def test_no_count_or_size_columns(self, unit):
        """Test that count/size/speed columns are not shown for any unit."""
        # Act
        pbar = create_progress_bar(total=100, description="Processing", unit=unit)
        column_types = {type(column) for column in pbar._progress.columns}

        # Assert
        assert MofNCompleteColumn not in column_types
        assert DownloadColumn not in column_types
        assert TransferSpeedColumn not in column_types


@pytest.mark.unit
class TestStepAwareColumn:
    """Test the _StepAwareColumn rendering logic."""

    def test_renders_step_count_for_step_task(self):
        """The source (step) task is rendered as a 'completed/total' count."""
        # Arrange
        with source_progress("countryInfo", total_steps=8) as group:
            group.advance_step()
            group.advance_step()
            group.advance_step()
            step_task = group._progress.tasks[0]
            column = _StepAwareColumn()

            # Act
            rendered = column.render(step_task)

            # Assert
            assert rendered.plain == "3/8"

    def test_renders_percentage_for_normal_task(self):
        """Ordinary task bars are rendered as a percentage."""
        # Arrange
        with create_progress_bar(total=200, description="Processing") as pbar:
            pbar.update(50)
            task = pbar._progress.tasks[0]
            column = _StepAwareColumn()

            # Act
            rendered = column.render(task)

            # Assert
            assert rendered.plain == "25%"


@pytest.mark.unit
class TestSourceProgress:
    """Test the source_progress grouping behavior."""

    def test_parent_step_task_tracks_pipeline_steps(self):
        """The parent task totals the steps and advances one per step."""
        # Act
        with source_progress("countryInfo", total_steps=8) as group:
            group.advance_step()
            group.advance_step()
            step_task = group._progress.tasks[0]

            # Assert
            assert step_task.total == 8
            assert step_task.completed == 2
            assert step_task.fields.get("is_step_task") is True

    def test_child_bars_attach_to_shared_display(self):
        """Bars created within the group share the group's progress display."""
        # Act
        with source_progress("countryInfo", total_steps=8) as group:
            with create_progress_bar(total=10, description="Loading") as pbar:
                # Assert
                assert pbar._progress is group._progress
                assert pbar._owns_progress is False

    def test_child_bars_are_removed_on_completion(self):
        """Finished child bars are removed so only the parent persists."""
        # Act
        with source_progress("countryInfo", total_steps=8) as group:
            with create_progress_bar(total=10, description="Loading"):
                # Two tasks visible while the child is active: parent + child
                assert len(group._progress.tasks) == 2

            # Child removed after completion, leaving only the parent
            assert len(group._progress.tasks) == 1
            assert group._progress.tasks[0].fields.get("is_step_task") is True

    def test_child_bar_keeps_raw_description_and_child_flag(self):
        """Child bars keep their raw description and are flagged as children."""
        # Act
        with source_progress("countryInfo", total_steps=8):
            with create_progress_bar(total=10, description="Loading") as pbar:
                child_task = pbar._progress.tasks[-1]

                # Assert
                assert child_task.description == "Loading"
                assert child_task.fields.get("is_child") is True

    def test_standalone_bar_outside_group(self):
        """Without an active group, bars own a standalone display."""
        # Act
        pbar = create_progress_bar(total=10, description="Loading")

        # Assert
        assert pbar._owns_progress is True
        assert pbar._task_id is None


@pytest.mark.unit
class TestDescriptionColumn:
    """Test the _DescriptionColumn rendering logic."""

    def test_renders_running_source_with_processing_label(self):
        """An in-progress source reads as 'Processing <name>'."""
        # Arrange
        with source_progress("countryInfo", total_steps=8) as group:
            step_task = group._progress.tasks[0]
            column = _DescriptionColumn(40)

            # Act
            rendered = column.render(step_task)

            # Assert
            assert rendered.plain == f"{_SOURCE_PROCESSING_LABEL}countryInfo"
            assert any("bold" in str(span.style) for span in rendered.spans)

    def test_renders_completed_source_with_processed_label(self):
        """A completed source reads as 'Processed <name>'."""
        # Arrange
        column = _DescriptionColumn(40)
        with source_progress("countryInfo", total_steps=2) as group:
            group.advance_step()
            group.advance_step()
            step_task = group._progress.tasks[0]

            # Act
            rendered = column.render(step_task)

            # Assert
            assert step_task.finished is True
            assert rendered.plain == f"{_SOURCE_PROCESSED_LABEL}countryInfo"

    def test_status_label_color_reflects_completion(self):
        """The status label changes color once the source completes."""
        # Arrange
        column = _DescriptionColumn(40)
        with source_progress("countryInfo", total_steps=2) as group:
            step_task = group._progress.tasks[0]
            running_label_style = column.render(step_task).spans[0].style

            group.advance_step()
            group.advance_step()
            done_label_style = column.render(step_task).spans[0].style

            # Assert
            assert running_label_style != done_label_style

    def test_renders_child_task_with_connector_spinner_and_dim(self):
        """An action (child) task is nested with a connector, spinner and dim text."""
        # Arrange
        with source_progress("countryInfo", total_steps=8):
            with create_progress_bar(total=10, description="Loading") as pbar:
                child_task = pbar._progress.tasks[-1]
                column = _DescriptionColumn(40)

                # Act
                rendered = column.render(child_task)

                # Assert
                assert rendered.plain.startswith(_CHILD_CONNECTOR)
                assert rendered.plain.endswith("Loading")
                assert len(rendered.plain) > len(_CHILD_CONNECTOR) + len("Loading")
                assert "dim" in str(rendered.style) or any(
                    "dim" in str(span.style) for span in rendered.spans
                )

    def test_renders_standalone_task_plainly(self):
        """A standalone task is rendered without nesting or emphasis."""
        # Arrange
        with create_progress_bar(total=10, description="Loading") as pbar:
            task = pbar._progress.tasks[0]
            column = _DescriptionColumn(40)

            # Act
            rendered = column.render(task)

            # Assert
            assert rendered.plain == "Loading"


@pytest.mark.unit
class TestStyledBarColumn:
    """Test the _StyledBarColumn coloring logic."""

    def test_source_bar_changes_color_on_completion(self):
        """A source bar uses the running color until done, then the done color."""
        # Arrange
        column = _StyledBarColumn()
        with source_progress("countryInfo", total_steps=2) as group:
            step_task = group._progress.tasks[0]

            # Act
            column.render(step_task)
            running_style = column.complete_style
            group.advance_step()
            group.advance_step()
            column.render(step_task)
            done_style = column.complete_style

            # Assert
            assert running_style != done_style

    def test_action_bar_uses_running_style(self):
        """Action (child) bars use the in-progress color."""
        # Arrange
        column = _StyledBarColumn()
        with source_progress("countryInfo", total_steps=8) as group:
            with create_progress_bar(total=10, description="Loading") as pbar:
                step_task = group._progress.tasks[0]
                child_task = pbar._progress.tasks[-1]

                # Act
                column.render(step_task)
                running_source_style = column.complete_style
                column.render(child_task)
                action_style = column.complete_style

                # Assert
                assert action_style == running_source_style


@pytest.mark.unit
class TestLayoutWidth:
    """Test dynamic layout and description width calculation."""

    def test_uses_terminal_width_on_wide_terminals(self):
        """Layout width follows the terminal when it is wider than default."""
        # Arrange
        console = Console(width=120, force_terminal=True, _environ={})

        # Act & Assert
        assert _layout_width(console) == 120
        assert _description_width(console) == 60

    def test_shrinks_layout_width_on_narrow_terminals(self):
        """Layout width follows the terminal when it is narrower than the cap."""
        # Arrange
        console = Console(width=60, force_terminal=True, _environ={})

        # Act & Assert
        assert _layout_width(console) == 60
        assert _description_width(console) == 30


@pytest.mark.unit
class TestGazetteerDisplay:
    """Test installer header and summary output."""

    def test_print_gazetteer_header(self):
        """Test that the install header includes the gazetteer name."""
        # Arrange
        from rich.console import Console

        console = Console(stderr=True, record=True, force_terminal=True)
        with patch(
            "geoparser.gazetteer.installer.utils.progress._console",
            return_value=console,
        ):
            # Act
            print_gazetteer_header("geonames-cities")

            # Assert
            output = console.export_text()
            assert "geonames-cities" in output
            assert "Installing:" not in output
            assert "sources to process" not in output

    def test_print_gazetteer_summary(self):
        """Test that the install summary shows right-aligned feature and name counts."""
        # Arrange
        from rich.console import Console

        console = Console(stderr=True, record=True, force_terminal=True)
        with patch(
            "geoparser.gazetteer.installer.utils.progress._console",
            return_value=console,
        ):
            # Act
            print_gazetteer_summary(3865, 47549)

            # Assert
            output = console.export_text()
            assert "Summary" in output
            assert "Features" in output
            assert "Names" in output
            assert "3,865" in output
            assert "47,549" in output
            assert "registered" not in output.lower()
