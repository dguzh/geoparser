"""
Unit tests for geoparser/cli/download.py

Tests the download CLI functionality.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest


@pytest.mark.unit
class TestGetBuiltinGazetteers:
    """Test _get_builtin_gazetteers() function."""

    @patch("geoparser.cli.download.files")
    def test_discovers_yaml_files_in_configs_directory(self, mock_files):
        """Test that YAML files are discovered from configs directory."""
        # Arrange
        from geoparser.cli.download import _get_builtin_gazetteers

        mock_configs_dir = Mock()
        mock_files.return_value.__truediv__.return_value = mock_configs_dir

        mock_yaml1 = Mock()
        mock_yaml1.name = "geonames.yaml"
        mock_yaml2 = Mock()
        mock_yaml2.name = "swissnames3d.yaml"
        mock_txt = Mock()
        mock_txt.name = "readme.txt"

        mock_configs_dir.iterdir.return_value = [mock_yaml1, mock_yaml2, mock_txt]

        # Act
        result = _get_builtin_gazetteers()

        # Assert
        assert "geonames" in result
        assert "swissnames3d" in result
        assert "readme" not in result  # Non-YAML files should be excluded

    @patch("geoparser.cli.download.files")
    def test_returns_empty_dict_when_no_yaml_files(self, mock_files):
        """Test that empty dict is returned when no YAML files found."""
        # Arrange
        from geoparser.cli.download import _get_builtin_gazetteers

        mock_configs_dir = Mock()
        mock_files.return_value.__truediv__.return_value = mock_configs_dir
        mock_configs_dir.iterdir.return_value = []

        # Act
        result = _get_builtin_gazetteers()

        # Assert
        assert result == {}

    @patch("geoparser.cli.download.files")
    def test_strips_yaml_extension_from_names(self, mock_files):
        """Test that .yaml extension is stripped from gazetteer names."""
        # Arrange
        from geoparser.cli.download import _get_builtin_gazetteers

        mock_configs_dir = Mock()
        mock_files.return_value.__truediv__.return_value = mock_configs_dir

        mock_yaml = Mock()
        mock_yaml.name = "my_gazetteer.yaml"
        mock_configs_dir.iterdir.return_value = [mock_yaml]

        # Act
        result = _get_builtin_gazetteers()

        # Assert
        assert "my_gazetteer" in result
        assert "my_gazetteer.yaml" not in result


@pytest.mark.unit
class TestDownloadCli:
    """Test download_cli() function."""

    @patch("geoparser.cli.download.GazetteerInstaller")
    @patch("geoparser.cli.download.Path")
    def test_installs_from_existing_file_path(self, mock_path_class, mock_installer):
        """Test that gazetteer is installed when config file exists."""
        # Arrange
        from geoparser.cli.download import download_cli

        mock_path = Mock()
        mock_path.exists.return_value = True
        mock_path_class.return_value = mock_path

        mock_installer_instance = Mock()
        mock_installer.return_value = mock_installer_instance

        # Act
        download_cli("path/to/config.yaml")

        # Assert
        mock_installer_instance.install.assert_called_once_with(mock_path)

    @patch("geoparser.cli.download.GazetteerInstaller")
    @patch("geoparser.cli.download._get_builtin_gazetteers")
    @patch("geoparser.cli.download.Path")
    def test_uses_builtin_gazetteer_when_name_matches(
        self, mock_path_class, mock_get_builtin, mock_installer
    ):
        """Test that built-in gazetteer is used when name matches."""
        # Arrange
        from geoparser.cli.download import download_cli

        mock_path = Mock()
        mock_path.exists.return_value = False
        mock_path_class.return_value = mock_path

        builtin_path = Path("/builtin/geonames.yaml")
        mock_get_builtin.return_value = {"geonames": builtin_path}

        mock_installer_instance = Mock()
        mock_installer.return_value = mock_installer_instance

        # Act
        download_cli("geonames")

        # Assert
        mock_installer_instance.install.assert_called_once_with(builtin_path)

    @patch("geoparser.cli.download._get_builtin_gazetteers")
    @patch("geoparser.cli.download.Path")
    def test_raises_error_when_config_not_found(
        self, mock_path_class, mock_get_builtin
    ):
        """Test that FileNotFoundError is raised when config doesn't exist."""
        # Arrange
        from geoparser.cli.download import download_cli

        mock_path = Mock()
        mock_path.exists.return_value = False
        mock_path_class.return_value = mock_path

        mock_get_builtin.return_value = {"geonames": Path("/builtin/geonames.yaml")}

        # Act & Assert
        with pytest.raises(FileNotFoundError, match="Gazetteer config not found"):
            download_cli("nonexistent")

    @patch("geoparser.cli.download._get_builtin_gazetteers")
    @patch("geoparser.cli.download.Path")
    def test_error_message_lists_available_gazetteers(
        self, mock_path_class, mock_get_builtin
    ):
        """Test that error message lists available built-in gazetteers."""
        # Arrange
        from geoparser.cli.download import download_cli

        mock_path = Mock()
        mock_path.exists.return_value = False
        mock_path_class.return_value = mock_path

        mock_get_builtin.return_value = {
            "geonames": Path("/builtin/geonames.yaml"),
            "swissnames3d": Path("/builtin/swissnames3d.yaml"),
        }

        # Act & Assert
        with pytest.raises(FileNotFoundError) as exc_info:
            download_cli("nonexistent")

        error_message = str(exc_info.value)
        assert "geonames" in error_message
        assert "swissnames3d" in error_message
        assert "Available built-in gazetteer configs" in error_message

    @patch("geoparser.cli.download.GazetteerInstaller")
    @patch("geoparser.cli.download._get_builtin_gazetteers")
    @patch("geoparser.cli.download.Path")
    def test_creates_installer_instance(
        self, mock_path_class, mock_get_builtin, mock_installer
    ):
        """Test that GazetteerInstaller is instantiated."""
        # Arrange
        from geoparser.cli.download import download_cli

        mock_path = Mock()
        mock_path.exists.return_value = True
        mock_path_class.return_value = mock_path

        mock_installer_instance = Mock()
        mock_installer.return_value = mock_installer_instance

        # Act
        download_cli("path/to/config.yaml")

        # Assert
        mock_installer.assert_called_once()
