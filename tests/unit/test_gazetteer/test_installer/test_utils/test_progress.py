"""
Unit tests for geoparser/gazetteer/installer/utils/progress.py

Tests the create_progress_bar utility function.
"""

import pytest
from tqdm.auto import tqdm

from geoparser.gazetteer.installer.utils.progress import create_progress_bar


@pytest.mark.unit
class TestCreateProgressBar:
    """Test create_progress_bar() function."""

    def test_creates_progress_bar_with_defaults(self):
        """Test creating progress bar with default unit."""
        # Act
        pbar = create_progress_bar(total=100, description="Processing")

        # Assert
        assert isinstance(pbar, tqdm)
        assert pbar.total == 100
        assert pbar.desc == "Processing"
        assert pbar.unit == "items"

        # Clean up
        pbar.close()

    def test_creates_progress_bar_with_custom_unit(self):
        """Test creating progress bar with custom unit."""
        # Act
        pbar = create_progress_bar(
            total=1000, description="Downloading", unit="records"
        )

        # Assert
        assert pbar.total == 1000
        assert pbar.desc == "Downloading"
        assert pbar.unit == "records"

        # Clean up
        pbar.close()

    def test_creates_progress_bar_with_bytes_unit(self):
        """Test creating progress bar with bytes unit enables scaling."""
        # Act
        pbar = create_progress_bar(total=1024, description="Transferring", unit="B")

        # Assert
        assert pbar.total == 1024
        assert pbar.unit == "B"
        assert pbar.unit_scale is True  # Should enable scaling for bytes

        # Clean up
        pbar.close()

    def test_creates_progress_bar_without_scaling_for_non_bytes(self):
        """Test that non-byte units don't enable scaling."""
        # Act
        pbar = create_progress_bar(total=100, description="Processing", unit="items")

        # Assert
        assert pbar.unit_scale is False

        # Clean up
        pbar.close()
