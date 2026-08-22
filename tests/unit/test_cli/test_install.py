"""
Unit tests for geoparser/cli/install.py

Tests the install, list and uninstall CLI functionality.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest


@pytest.mark.unit
class TestGetBuiltinGazetteers:
    """Test _get_builtin_gazetteers() function."""

    @patch("geoparser.cli.install.files")
    def test_discovers_yaml_files_in_configs_directory(self, mock_files):
        """Test that YAML files are discovered from configs directory."""
        # Arrange
        from geoparser.cli.install import _get_builtin_gazetteers

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

    @patch("geoparser.cli.install.files")
    def test_returns_empty_dict_when_no_yaml_files(self, mock_files):
        """Test that empty dict is returned when no YAML files found."""
        # Arrange
        from geoparser.cli.install import _get_builtin_gazetteers

        mock_configs_dir = Mock()
        mock_files.return_value.__truediv__.return_value = mock_configs_dir
        mock_configs_dir.iterdir.return_value = []

        # Act
        result = _get_builtin_gazetteers()

        # Assert
        assert result == {}

    @patch("geoparser.cli.install.files")
    def test_strips_yaml_extension_from_names(self, mock_files):
        """Test that .yaml extension is stripped from gazetteer names."""
        # Arrange
        from geoparser.cli.install import _get_builtin_gazetteers

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
class TestInstallCli:
    """Test install_cli() function."""

    @patch("geoparser.cli.install.GazetteerBuilder")
    @patch("geoparser.cli.install.Path")
    def test_installs_from_existing_file_path(self, mock_path_class, mock_builder):
        """Test that gazetteer is built when config file exists."""
        # Arrange
        from geoparser.cli.install import install_cli

        mock_path = Mock()
        mock_path.exists.return_value = True
        mock_path_class.return_value = mock_path

        mock_builder_instance = Mock()
        mock_builder.return_value = mock_builder_instance

        # Act
        install_cli("path/to/config.yaml")

        # Assert
        mock_builder_instance.build.assert_called_once_with(mock_path)

    @patch("geoparser.cli.install.GazetteerBuilder")
    @patch("geoparser.cli.install._get_builtin_gazetteers")
    @patch("geoparser.cli.install.Path")
    def test_uses_builtin_gazetteer_when_name_matches(
        self, mock_path_class, mock_get_builtin, mock_builder
    ):
        """Test that built-in gazetteer is used when name matches."""
        # Arrange
        from geoparser.cli.install import install_cli

        mock_path = Mock()
        mock_path.exists.return_value = False
        mock_path_class.return_value = mock_path

        builtin_path = Path("/builtin/geonames.yaml")
        mock_get_builtin.return_value = {"geonames": builtin_path}

        mock_builder_instance = Mock()
        mock_builder.return_value = mock_builder_instance

        # Act
        install_cli("geonames")

        # Assert
        mock_builder_instance.build.assert_called_once_with(builtin_path)

    @patch("geoparser.cli.install._get_builtin_gazetteers")
    @patch("geoparser.cli.install.Path")
    def test_raises_error_when_config_not_found(
        self, mock_path_class, mock_get_builtin
    ):
        """Test that FileNotFoundError is raised when config doesn't exist."""
        # Arrange
        from geoparser.cli.install import install_cli

        mock_path = Mock()
        mock_path.exists.return_value = False
        mock_path_class.return_value = mock_path

        mock_get_builtin.return_value = {"geonames": Path("/builtin/geonames.yaml")}

        # Act & Assert
        with pytest.raises(FileNotFoundError, match="Gazetteer config not found"):
            install_cli("nonexistent")

    @patch("geoparser.cli.install._get_builtin_gazetteers")
    @patch("geoparser.cli.install.Path")
    def test_error_message_lists_available_gazetteers(
        self, mock_path_class, mock_get_builtin
    ):
        """Test that error message lists available built-in gazetteers."""
        # Arrange
        from geoparser.cli.install import install_cli

        mock_path = Mock()
        mock_path.exists.return_value = False
        mock_path_class.return_value = mock_path

        mock_get_builtin.return_value = {
            "geonames": Path("/builtin/geonames.yaml"),
            "swissnames3d": Path("/builtin/swissnames3d.yaml"),
        }

        # Act & Assert
        with pytest.raises(FileNotFoundError) as exc_info:
            install_cli("nonexistent")

        error_message = str(exc_info.value)
        assert "geonames" in error_message
        assert "swissnames3d" in error_message
        assert "Available built-in gazetteer configs" in error_message

    @patch("geoparser.cli.install.GazetteerBuilder")
    @patch("geoparser.cli.install._get_builtin_gazetteers")
    @patch("geoparser.cli.install.Path")
    def test_creates_builder_instance(
        self, mock_path_class, mock_get_builtin, mock_builder
    ):
        """Test that GazetteerBuilder is instantiated."""
        # Arrange
        from geoparser.cli.install import install_cli

        mock_path = Mock()
        mock_path.exists.return_value = True
        mock_path_class.return_value = mock_path

        mock_builder_instance = Mock()
        mock_builder.return_value = mock_builder_instance

        # Act
        install_cli("path/to/config.yaml")

        # Assert
        mock_builder.assert_called_once()


@pytest.mark.unit
class TestListCli:
    """Test list_cli() function."""

    @patch("geoparser.cli.install.list_artifacts")
    def test_reports_when_no_gazetteers_installed(self, mock_list, capsys):
        """Test that an empty install base is reported."""
        from geoparser.cli.install import list_cli

        mock_list.return_value = []

        list_cli()

        assert "No gazetteers installed" in capsys.readouterr().out

    @patch("geoparser.cli.install.artifact_path")
    @patch("geoparser.cli.install.list_artifacts")
    def test_lists_installed_gazetteers_with_size(
        self, mock_list, mock_artifact_path, capsys
    ):
        """Test that installed gazetteers are listed with their size."""
        from geoparser.cli.install import list_cli

        mock_list.return_value = ["andorranames"]
        mock_artifact_path.return_value.stat.return_value.st_size = 2 * 1024 * 1024

        list_cli()

        output = capsys.readouterr().out
        assert "andorranames" in output
        assert "2.0 MB" in output


@pytest.mark.unit
class TestUninstallCli:
    """Test uninstall_cli() function."""

    @patch("geoparser.cli.install.uninstall")
    def test_removes_installed_gazetteer(self, mock_uninstall, capsys):
        """Test that an installed gazetteer is removed."""
        from geoparser.cli.install import uninstall_cli

        mock_uninstall.return_value = True

        uninstall_cli("andorranames")

        mock_uninstall.assert_called_once_with("andorranames")
        assert "Removed gazetteer 'andorranames'" in capsys.readouterr().out

    @patch("geoparser.cli.install.uninstall")
    def test_exits_with_error_when_not_installed(self, mock_uninstall):
        """Test that uninstalling a missing gazetteer exits with an error."""
        import typer

        from geoparser.cli.install import uninstall_cli

        mock_uninstall.return_value = False

        with pytest.raises(typer.Exit):
            uninstall_cli("missing")
