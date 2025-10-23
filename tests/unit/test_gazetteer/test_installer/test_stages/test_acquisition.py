"""
Unit tests for geoparser/gazetteer/installer/stages/acquisition.py

Tests the AcquisitionStage class.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from geoparser.gazetteer.installer.model import (
    AttributesConfig,
    DataType,
    OriginalAttributeConfig,
    SourceConfig,
    SourceType,
)
from geoparser.gazetteer.installer.stages.acquisition import AcquisitionStage


@pytest.mark.unit
class TestAcquisitionStageConstants:
    """Test AcquisitionStage constants."""

    def test_has_request_timeout_constant(self):
        """Test that REQUEST_TIMEOUT constant is defined."""
        assert AcquisitionStage.REQUEST_TIMEOUT == 30

    def test_has_download_chunk_size_constant(self):
        """Test that DOWNLOAD_CHUNK_SIZE constant is defined."""
        assert AcquisitionStage.DOWNLOAD_CHUNK_SIZE == 8192


@pytest.mark.unit
class TestAcquisitionStageInit:
    """Test AcquisitionStage initialization."""

    def test_creates_downloads_directory(self):
        """Test that downloads directory is created on initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            downloads_dir = Path(temp_dir) / "downloads"

            # Act
            stage = AcquisitionStage(downloads_dir)

            # Assert
            assert downloads_dir.exists()
            assert stage.downloads_directory == downloads_dir

    def test_sets_name_and_description(self):
        """Test that stage name and description are set."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Act
            stage = AcquisitionStage(Path(temp_dir))

            # Assert
            assert stage.name == "Acquisition"
            assert stage.description == "Download and extract source files"


@pytest.mark.unit
class TestAcquisitionStageCleanup:
    """Test AcquisitionStage.cleanup() method."""

    def test_removes_downloads_directory(self):
        """Test that cleanup removes the downloads directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            downloads_dir = Path(temp_dir) / "test_downloads"
            stage = AcquisitionStage(downloads_dir)

            # Create a file in the downloads directory
            test_file = downloads_dir / "test.txt"
            test_file.write_text("test")

            # Act
            stage.cleanup()

            # Assert
            assert not downloads_dir.exists()

    def test_cleanup_handles_nonexistent_directory(self):
        """Test that cleanup handles non-existent directory gracefully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            downloads_dir = Path(temp_dir) / "nonexistent"
            stage = AcquisitionStage(downloads_dir)

            # Manually remove the directory
            downloads_dir.rmdir()

            # Act - should not raise an error
            stage.cleanup()

            # Assert
            assert not downloads_dir.exists()


@pytest.mark.unit
class TestAcquisitionStageValidateLocalPath:
    """Test AcquisitionStage._validate_local_path() method."""

    def test_returns_path_when_exists(self):
        """Test that existing local path is returned."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Arrange
            local_file = Path(temp_dir) / "test.csv"
            local_file.write_text("test")

            source = SourceConfig(
                name="test",
                path=str(local_file),
                file="test.csv",
                type=SourceType.TABULAR,
                separator=",",
                attributes=AttributesConfig(
                    original=[OriginalAttributeConfig(name="id", type=DataType.INTEGER)]
                ),
            )

            stage = AcquisitionStage(Path(temp_dir))

            # Act
            result = stage._validate_local_path(source)

            # Assert
            assert result == local_file

    def test_raises_error_when_path_not_exists(self):
        """Test that error is raised when local path doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Arrange
            source = SourceConfig(
                name="test",
                path="/nonexistent/path/data.csv",
                file="data.csv",
                type=SourceType.TABULAR,
                separator=",",
                attributes=AttributesConfig(
                    original=[OriginalAttributeConfig(name="id", type=DataType.INTEGER)]
                ),
            )

            stage = AcquisitionStage(Path(temp_dir))

            # Act & Assert
            with pytest.raises(FileNotFoundError, match="Local path does not exist"):
                stage._validate_local_path(source)


@pytest.mark.unit
class TestAcquisitionStageResolveSourcePath:
    """Test AcquisitionStage._resolve_source_path() method."""

    @patch.object(AcquisitionStage, "_download_file")
    def test_calls_download_for_url_source(self, mock_download):
        """Test that _download_file is called for URL sources."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Arrange
            source = SourceConfig(
                name="test",
                url="http://example.com/data.csv",
                file="data.csv",
                type=SourceType.TABULAR,
                separator=",",
                attributes=AttributesConfig(
                    original=[OriginalAttributeConfig(name="id", type=DataType.INTEGER)]
                ),
            )

            stage = AcquisitionStage(Path(temp_dir))
            mock_download.return_value = Path("/fake/path/data.csv")

            # Act
            result = stage._resolve_source_path(source)

            # Assert
            mock_download.assert_called_once_with(source)
            assert result == Path("/fake/path/data.csv")

    @patch.object(AcquisitionStage, "_validate_local_path")
    def test_calls_validate_for_local_source(self, mock_validate):
        """Test that _validate_local_path is called for local sources."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Arrange
            source = SourceConfig(
                name="test",
                path="/local/data.csv",
                file="data.csv",
                type=SourceType.TABULAR,
                separator=",",
                attributes=AttributesConfig(
                    original=[OriginalAttributeConfig(name="id", type=DataType.INTEGER)]
                ),
            )

            stage = AcquisitionStage(Path(temp_dir))
            mock_validate.return_value = Path("/local/data.csv")

            # Act
            result = stage._resolve_source_path(source)

            # Assert
            mock_validate.assert_called_once_with(source)
            assert result == Path("/local/data.csv")
