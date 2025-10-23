"""
Unit tests for geoparser/__main__.py

Tests the main entry point.
"""

from unittest.mock import patch

import pytest


@pytest.mark.unit
class TestMain:
    """Test main() function."""

    @patch("geoparser.__main__.app")
    def test_main_calls_app(self, mock_app):
        """Test that main() calls the CLI app."""
        # Arrange
        from geoparser.__main__ import main

        # Act
        main()

        # Assert
        mock_app.assert_called_once()

    @patch("geoparser.__main__.app")
    def test_main_passes_no_arguments(self, mock_app):
        """Test that main() calls app with no arguments."""
        # Arrange
        from geoparser.__main__ import main

        # Act
        main()

        # Assert
        mock_app.assert_called_once_with()
