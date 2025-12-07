"""
Unit tests for geoparser/__main__.py

Tests the main entry point for the geoparser module.
"""

import subprocess
import sys
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

    def test_main_module_execution(self):
        """Test running the module directly with python -m geoparser."""
        # Arrange & Act
        # Use longer timeout on Windows where subprocess can be slower
        timeout = 60 if sys.platform == "win32" else 30

        result = subprocess.run(
            [sys.executable, "-m", "geoparser", "--help"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        # Assert
        assert result.returncode == 0
        assert "Usage:" in result.stdout or "usage:" in result.stdout.lower()
