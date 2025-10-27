"""
Unit tests for geoparser/__main__.py

Tests the main entry point for the geoparser module.
"""

from unittest.mock import patch

import pytest


@pytest.mark.unit
class TestMain:
    """Test __main__.py entry point."""

    @patch("geoparser.__main__.app")
    def test_main_calls_app(self, mock_app):
        """Test that main() function calls the app."""
        # Arrange
        from geoparser.__main__ import main

        # Act
        main()

        # Assert
        mock_app.assert_called_once()
