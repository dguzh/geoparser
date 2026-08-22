"""
Unit tests for geoparser/cli/download.py

Tests the deprecated download CLI command.
"""

from unittest.mock import patch

import pytest
import typer


@pytest.mark.unit
class TestDownloadCli:
    """Test deprecated download_cli() command."""

    @patch("geoparser.cli.download.typer.secho")
    def test_does_not_install_gazetteer(self, mock_secho):
        """Test that download_cli does not install a gazetteer."""
        from geoparser.cli.download import download_cli

        with pytest.raises(typer.Exit) as exc_info:
            download_cli("geonames")

        assert exc_info.value.exit_code == 1

    @patch("geoparser.cli.download.typer.secho")
    def test_prints_install_command(self, mock_secho):
        """Test that download_cli prints the replacement install command."""
        from geoparser.cli.download import download_cli

        with pytest.raises(typer.Exit):
            download_cli("geonames")

        mock_secho.assert_called_once()
        message = mock_secho.call_args[0][0]
        assert "install" in message.lower()
        assert "geonames" in message
