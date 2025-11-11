"""
Unit tests for geoparser/gazetteer/installer/stages/acquisition.py

Tests the AcquisitionStage class.
"""

import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest
import requests_mock

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


@pytest.mark.unit
class TestAcquisitionStageDownloadFile:
    """Test AcquisitionStage._download_file() and related methods."""

    def test_downloads_file_when_not_cached(self):
        """Test that file is downloaded when not already cached."""
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

            with requests_mock.Mocker() as m:
                # Mock the HTTP response
                m.get(
                    "http://example.com/data.csv",
                    text="id,name\n1,test",
                    headers={"content-length": "16"},
                )

                # Act
                result = stage._download_file(source)

                # Assert
                assert result.exists()
                assert result.name == "data.csv"
                assert result.read_text() == "id,name\n1,test"

    def test_skips_download_when_file_exists_with_same_size(self):
        """Test that download is skipped when local file matches remote size."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Arrange
            downloads_dir = Path(temp_dir)
            local_file = downloads_dir / "data.csv"
            local_file.write_text("id,name\n1,test")

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

            stage = AcquisitionStage(downloads_dir)

            with requests_mock.Mocker() as m:
                # Mock HEAD request with matching content-length
                m.head(
                    "http://example.com/data.csv",
                    headers={"content-length": str(local_file.stat().st_size)},
                )

                # Act
                result = stage._download_file(source)

                # Assert - Should return existing file without downloading
                assert result == local_file
                # GET should not be called
                assert not any(req.method == "GET" for req in m.request_history)

    def test_downloads_when_head_request_fails(self):
        """Test that download proceeds when HEAD request fails."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Arrange
            downloads_dir = Path(temp_dir)
            local_file = downloads_dir / "data.csv"
            local_file.write_text("old content")

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

            stage = AcquisitionStage(downloads_dir)

            with requests_mock.Mocker() as m:
                # Mock HEAD request failure
                m.head("http://example.com/data.csv", status_code=500)
                # Mock successful GET request
                m.get(
                    "http://example.com/data.csv",
                    text="new content",
                    headers={"content-length": "11"},
                )

                # Act
                result = stage._download_file(source)

                # Assert - Should download despite HEAD failure
                assert result.read_text() == "new content"

    def test_downloads_when_content_length_is_invalid(self):
        """Test that download proceeds when content-length header is invalid."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Arrange
            downloads_dir = Path(temp_dir)
            local_file = downloads_dir / "data.csv"
            local_file.write_text("old content")

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

            stage = AcquisitionStage(downloads_dir)

            with requests_mock.Mocker() as m:
                # Mock HEAD with invalid content-length
                m.head(
                    "http://example.com/data.csv", headers={"content-length": "invalid"}
                )
                # Mock successful GET request
                m.get(
                    "http://example.com/data.csv",
                    text="new content",
                    headers={"content-length": "11"},
                )

                # Act
                result = stage._download_file(source)

                # Assert - Should download despite invalid content-length
                assert result.read_text() == "new content"

    def test_downloads_when_size_differs(self):
        """Test that file is downloaded when size differs from remote."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Arrange
            downloads_dir = Path(temp_dir)
            local_file = downloads_dir / "data.csv"
            local_file.write_text("old")

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

            stage = AcquisitionStage(downloads_dir)

            with requests_mock.Mocker() as m:
                # Mock HEAD with different size
                m.head("http://example.com/data.csv", headers={"content-length": "100"})
                # Mock GET request
                m.get(
                    "http://example.com/data.csv",
                    text="new content",
                    headers={"content-length": "11"},
                )

                # Act
                result = stage._download_file(source)

                # Assert
                assert result.read_text() == "new content"


@pytest.mark.unit
class TestAcquisitionStageResolveFilePath:
    """Test AcquisitionStage._resolve_file_path() and related methods."""

    def test_returns_file_when_path_matches_target(self):
        """Test that file is returned when filename matches target."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Arrange
            test_file = Path(temp_dir) / "data.csv"
            test_file.write_text("test data")

            source = SourceConfig(
                name="test",
                path=str(test_file),
                file="data.csv",
                type=SourceType.TABULAR,
                separator=",",
                attributes=AttributesConfig(
                    original=[OriginalAttributeConfig(name="id", type=DataType.INTEGER)]
                ),
            )

            stage = AcquisitionStage(Path(temp_dir))

            # Act
            result = stage._resolve_file_path(source, test_file)

            # Assert
            assert result == test_file

    def test_raises_error_when_file_name_doesnt_match(self):
        """Test that error is raised when non-zip file doesn't match target name."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Arrange
            test_file = Path(temp_dir) / "wrong_name.csv"
            test_file.write_text("test data")

            source = SourceConfig(
                name="test",
                path=str(test_file),
                file="expected.csv",
                type=SourceType.TABULAR,
                separator=",",
                attributes=AttributesConfig(
                    original=[OriginalAttributeConfig(name="id", type=DataType.INTEGER)]
                ),
            )

            stage = AcquisitionStage(Path(temp_dir))

            # Act & Assert
            with pytest.raises(
                FileNotFoundError, match="File 'expected.csv' not found"
            ):
                stage._resolve_file_path(source, test_file)

    def test_finds_file_in_directory(self):
        """Test that target file is found in a directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Arrange
            data_dir = Path(temp_dir) / "data"
            data_dir.mkdir()
            target_file = data_dir / "target.csv"
            target_file.write_text("test data")

            source = SourceConfig(
                name="test",
                path=str(data_dir),
                file="target.csv",
                type=SourceType.TABULAR,
                separator=",",
                attributes=AttributesConfig(
                    original=[OriginalAttributeConfig(name="id", type=DataType.INTEGER)]
                ),
            )

            stage = AcquisitionStage(Path(temp_dir))

            # Act
            result = stage._resolve_file_path(source, data_dir)

            # Assert
            assert result == target_file

    def test_finds_file_in_nested_directory(self):
        """Test that target file is found in nested directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Arrange
            data_dir = Path(temp_dir) / "data"
            nested_dir = data_dir / "subdir" / "nested"
            nested_dir.mkdir(parents=True)
            target_file = nested_dir / "target.csv"
            target_file.write_text("test data")

            source = SourceConfig(
                name="test",
                path=str(data_dir),
                file="target.csv",
                type=SourceType.TABULAR,
                separator=",",
                attributes=AttributesConfig(
                    original=[OriginalAttributeConfig(name="id", type=DataType.INTEGER)]
                ),
            )

            stage = AcquisitionStage(Path(temp_dir))

            # Act
            result = stage._resolve_file_path(source, data_dir)

            # Assert
            assert result == target_file

    def test_extracts_zip_and_finds_file(self):
        """Test that ZIP archive is extracted and target file is found."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Arrange
            zip_path = Path(temp_dir) / "archive.zip"
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("data/target.csv", "test data")

            source = SourceConfig(
                name="test",
                url="http://example.com/archive.zip",
                file="target.csv",
                type=SourceType.TABULAR,
                separator=",",
                attributes=AttributesConfig(
                    original=[OriginalAttributeConfig(name="id", type=DataType.INTEGER)]
                ),
            )

            stage = AcquisitionStage(Path(temp_dir))

            # Act
            result = stage._resolve_file_path(source, zip_path)

            # Assert
            assert result.exists()
            assert result.name == "target.csv"
            assert result.read_text() == "test data"

    def test_skips_extraction_when_already_extracted(self):
        """Test that extraction is skipped when files already extracted."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Arrange
            zip_path = Path(temp_dir) / "archive.zip"
            extraction_dir = Path(temp_dir) / "archive"
            extraction_dir.mkdir()
            target_file = extraction_dir / "target.csv"
            target_file.write_text("existing content")

            # Create ZIP with different content
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("target.csv", "zip content")

            # Make extracted file newer than ZIP
            import time

            time.sleep(0.01)
            target_file.touch()

            source = SourceConfig(
                name="test",
                url="http://example.com/archive.zip",
                file="target.csv",
                type=SourceType.TABULAR,
                separator=",",
                attributes=AttributesConfig(
                    original=[OriginalAttributeConfig(name="id", type=DataType.INTEGER)]
                ),
            )

            stage = AcquisitionStage(Path(temp_dir))

            # Act
            result = stage._resolve_file_path(source, zip_path)

            # Assert - Should use existing file
            assert result.read_text() == "existing content"

    def test_raises_error_when_file_not_in_zip(self):
        """Test that error is raised when target file not found in ZIP."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Arrange
            zip_path = Path(temp_dir) / "archive.zip"
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("wrong.csv", "test data")

            source = SourceConfig(
                name="test",
                url="http://example.com/archive.zip",
                file="target.csv",
                type=SourceType.TABULAR,
                separator=",",
                attributes=AttributesConfig(
                    original=[OriginalAttributeConfig(name="id", type=DataType.INTEGER)]
                ),
            )

            stage = AcquisitionStage(Path(temp_dir))

            # Act & Assert
            with pytest.raises(
                FileNotFoundError, match="File 'target.csv' not found in archive"
            ):
                stage._resolve_file_path(source, zip_path)

    def test_returns_extraction_dir_when_it_matches_target_name(self):
        """Test that extraction directory is returned when its name matches target."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Arrange
            zip_path = Path(temp_dir) / "data.zip"
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("file.txt", "test")

            source = SourceConfig(
                name="test",
                url="http://example.com/data.zip",
                file="data",  # Target is the directory name
                type=SourceType.TABULAR,
                separator=",",
                attributes=AttributesConfig(
                    original=[OriginalAttributeConfig(name="id", type=DataType.INTEGER)]
                ),
            )

            stage = AcquisitionStage(Path(temp_dir))

            # Act
            result = stage._resolve_file_path(source, zip_path)

            # Assert
            # Should return the extraction directory itself
            assert result.is_dir()
            assert result.name == "data"


@pytest.mark.unit
class TestAcquisitionStageFindTargetFileQuiet:
    """Test AcquisitionStage._find_target_file_quiet() method."""

    def test_returns_none_when_file_not_found(self):
        """Test that None is returned when file is not found."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Arrange
            directory = Path(temp_dir)
            stage = AcquisitionStage(directory)

            # Act
            result = stage._find_target_file_quiet(directory, "nonexistent.csv")

            # Assert
            assert result is None

    def test_returns_path_when_file_found(self):
        """Test that path is returned when file is found."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Arrange
            directory = Path(temp_dir)
            target_file = directory / "target.csv"
            target_file.write_text("test")

            stage = AcquisitionStage(directory)

            # Act
            result = stage._find_target_file_quiet(directory, "target.csv")

            # Assert
            assert result == target_file
