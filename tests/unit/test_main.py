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
        # The CLI resolves its heavy imports per command, so `--help` is a
        # fraction of a second. The budget stays generous anyway: a loaded CI
        # runner should not turn a slow start-up into a spurious failure, and
        # Windows spawns subprocesses more slowly still.
        timeout = 240 if sys.platform == "win32" else 120

        result = subprocess.run(
            [sys.executable, "-m", "geoparser", "--help"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        # Assert
        assert result.returncode == 0
        assert "Usage:" in result.stdout or "usage:" in result.stdout.lower()

    def test_help_does_not_import_the_heavy_stack(self):
        """
        `--help` must not pay for torch, spaCy or duckdb.

        Registering the annotator and install commands used to import the
        FastAPI app and the build pipeline at module scope, which made every
        CLI invocation load the whole machine-learning stack. This pins the
        commands staying lazily imported.
        """
        # Arrange & Act
        probe = (
            "import runpy, sys\n"
            "sys.argv = ['geoparser', '--help']\n"
            "try:\n"
            "    runpy.run_module('geoparser', run_name='__main__')\n"
            "except SystemExit:\n"
            "    pass\n"
            "heavy = {'torch', 'spacy', 'thinc', 'transformers', 'duckdb'}\n"
            "print(sorted(heavy & set(sys.modules)))\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", probe],
            capture_output=True,
            text=True,
            timeout=240 if sys.platform == "win32" else 120,
        )

        # Assert
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip().endswith("[]"), (
            f"CLI --help imported heavy modules: {result.stdout.strip()}"
        )
