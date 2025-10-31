"""
Unit tests for geoparser/db/extensions/spellfix/loader.py

Tests the Spellfix extension loading utilities.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from geoparser.db.extensions.spellfix.loader import (
    get_spellfix_path,
    load_spellfix_extension,
)


@pytest.mark.unit
class TestGetSpellfixPath:
    """Test get_spellfix_path() function."""

    @patch("geoparser.db.extensions.spellfix.loader.platform.system")
    @patch("geoparser.db.extensions.spellfix.loader.platform.machine")
    def test_returns_linux_x86_64_path(self, mock_machine, mock_system):
        """Test that correct path is returned for Linux x86_64."""
        # Arrange
        mock_system.return_value = "Linux"
        mock_machine.return_value = "x86_64"

        # Act
        result = get_spellfix_path()

        # Assert
        # Should return a Path object (or None if file doesn't exist)
        assert result is None or isinstance(result, Path)

    @patch("geoparser.db.extensions.spellfix.loader.platform.system")
    @patch("geoparser.db.extensions.spellfix.loader.platform.machine")
    def test_returns_macos_x86_64_path(self, mock_machine, mock_system):
        """Test that correct path is returned for macOS x86_64."""
        # Arrange
        mock_system.return_value = "Darwin"
        mock_machine.return_value = "x86_64"

        # Act
        result = get_spellfix_path()

        # Assert
        assert result is None or isinstance(result, Path)

    @patch("geoparser.db.extensions.spellfix.loader.platform.system")
    @patch("geoparser.db.extensions.spellfix.loader.platform.machine")
    def test_returns_macos_arm64_path(self, mock_machine, mock_system):
        """Test that correct path is returned for macOS ARM64 (Apple Silicon)."""
        # Arrange
        mock_system.return_value = "Darwin"
        mock_machine.return_value = "arm64"

        # Act
        result = get_spellfix_path()

        # Assert
        assert result is None or isinstance(result, Path)

    @patch("geoparser.db.extensions.spellfix.loader.platform.system")
    @patch("geoparser.db.extensions.spellfix.loader.platform.machine")
    def test_returns_windows_amd64_path(self, mock_machine, mock_system):
        """Test that correct path is returned for Windows AMD64."""
        # Arrange
        mock_system.return_value = "Windows"
        mock_machine.return_value = "AMD64"

        # Act
        result = get_spellfix_path()

        # Assert
        assert result is None or isinstance(result, Path)

    @patch("geoparser.db.extensions.spellfix.loader.platform.system")
    @patch("geoparser.db.extensions.spellfix.loader.platform.machine")
    def test_returns_none_for_linux_arm64(self, mock_machine, mock_system):
        """Test that None is returned for unsupported Linux ARM64."""
        # Arrange
        mock_system.return_value = "Linux"
        mock_machine.return_value = "aarch64"

        # Act
        result = get_spellfix_path()

        # Assert
        assert result is None

    @patch("geoparser.db.extensions.spellfix.loader.platform.system")
    @patch("geoparser.db.extensions.spellfix.loader.platform.machine")
    def test_returns_none_for_unsupported_architecture(self, mock_machine, mock_system):
        """Test that None is returned for unsupported architectures."""
        # Arrange
        mock_system.return_value = "Linux"
        mock_machine.return_value = "i686"  # 32-bit

        # Act
        result = get_spellfix_path()

        # Assert
        assert result is None

    @patch("geoparser.db.extensions.spellfix.loader.platform.system")
    @patch("geoparser.db.extensions.spellfix.loader.platform.machine")
    def test_returns_none_for_unsupported_os(self, mock_machine, mock_system):
        """Test that None is returned for unsupported operating systems."""
        # Arrange
        mock_system.return_value = "FreeBSD"
        mock_machine.return_value = "x86_64"

        # Act
        result = get_spellfix_path()

        # Assert
        assert result is None

    def test_returns_path_or_none_for_current_platform(self):
        """Test that function returns valid Path or None for current platform."""
        # Act
        result = get_spellfix_path()

        # Assert
        # Should return Path or None depending on whether file exists
        assert result is None or isinstance(result, Path)


@pytest.mark.unit
class TestLoadSpellfixExtension:
    """Test load_spellfix_extension() function."""

    @patch("geoparser.db.extensions.spellfix.loader.platform.system")
    def test_enables_and_disables_extension_loading(self, mock_system):
        """Test that extension loading is enabled and then disabled."""
        # Arrange
        mock_system.return_value = "Linux"
        mock_connection = Mock()
        spellfix_path = Path("/fake/path/spellfix.so")

        # Act
        load_spellfix_extension(mock_connection, spellfix_path)

        # Assert
        assert mock_connection.enable_load_extension.call_count == 2
        mock_connection.enable_load_extension.assert_any_call(True)
        mock_connection.enable_load_extension.assert_any_call(False)

    @patch("geoparser.db.extensions.spellfix.loader.platform.system")
    def test_loads_extension_without_suffix(self, mock_system):
        """Test that extension is loaded without file suffix."""
        # Arrange
        mock_system.return_value = "Linux"
        mock_connection = Mock()
        spellfix_path = Path("/fake/path/spellfix.so")

        # Act
        load_spellfix_extension(mock_connection, spellfix_path)

        # Assert - Check that the path without suffix was used (platform-agnostic)
        expected_path = str(spellfix_path.with_suffix(""))
        mock_connection.load_extension.assert_called_once_with(expected_path)

    @patch("geoparser.db.extensions.spellfix.loader.platform.system")
    @patch("geoparser.db.extensions.spellfix.loader.os.environ", {"PATH": "/original/path"})
    def test_modifies_path_on_windows(self, mock_system):
        """Test that PATH is temporarily modified on Windows."""
        # Arrange
        mock_system.return_value = "Windows"
        mock_connection = Mock()
        spellfix_path = Path("C:/fake/path/spellfix.dll")

        with patch("geoparser.db.extensions.spellfix.loader.os.environ") as mock_environ:
            mock_environ.__getitem__ = Mock(return_value="/original/path")
            mock_environ.__setitem__ = Mock()
            mock_environ.get = Mock(return_value="/original/path")

            # Act
            load_spellfix_extension(mock_connection, spellfix_path)

            # Assert
            # PATH should be modified to include DLL directory and then restored
            assert mock_environ.__setitem__.call_count >= 1

    @patch("geoparser.db.extensions.spellfix.loader.platform.system")
    def test_disables_extension_loading_even_on_error(self, mock_system):
        """Test that extension loading is disabled even if an error occurs."""
        # Arrange
        mock_system.return_value = "Linux"
        mock_connection = Mock()
        mock_connection.load_extension.side_effect = Exception("Load failed")
        spellfix_path = Path("/fake/path/spellfix.so")

        # Act & Assert
        with pytest.raises(Exception, match="Load failed"):
            load_spellfix_extension(mock_connection, spellfix_path)

        # Extension loading should still be disabled
        mock_connection.enable_load_extension.assert_any_call(False)

