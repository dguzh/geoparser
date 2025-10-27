"""
Unit tests for geoparser/cli/annotator.py

Tests the annotator CLI wrapper.
"""

from unittest.mock import patch

import pytest


@pytest.mark.unit
class TestAnnotatorCli:
    """Test annotator_cli() function."""

    @patch("geoparser.cli.annotator.run")
    def test_calls_annotator_run(self, mock_run):
        """Test that annotator_cli calls the annotator run function."""
        # Arrange
        from geoparser.cli.annotator import annotator_cli

        # Act
        annotator_cli()

        # Assert
        mock_run.assert_called_once()

    @patch("geoparser.cli.annotator.run")
    def test_passes_no_arguments_to_run(self, mock_run):
        """Test that no arguments are passed to run()."""
        # Arrange
        from geoparser.cli.annotator import annotator_cli

        # Act
        annotator_cli()

        # Assert
        mock_run.assert_called_once_with()
