"""
Unit tests for geoparser/cli/app.py

Tests the CLI application setup.
"""

import pytest


@pytest.mark.unit
class TestCliApp:
    """Test CLI app setup."""

    def test_creates_typer_app(self):
        """Test that Typer app is created."""
        # This test verifies the module can be imported without errors
        # The actual app object is created at module level
        from geoparser.cli.app import app

        # Assert app exists and is a Typer instance
        assert app is not None

    def test_app_has_annotator_command(self):
        """Test that app has annotator command registered."""
        # Arrange
        from geoparser.cli.app import app

        # Act - Get registered commands
        commands = {cmd.name: cmd for cmd in app.registered_commands}

        # Assert
        assert "annotator" in commands

    def test_app_has_download_command(self):
        """Test that app has download command registered."""
        # Arrange
        from geoparser.cli.app import app

        # Act - Get registered commands
        commands = {cmd.name: cmd for cmd in app.registered_commands}

        # Assert
        assert "download" in commands
