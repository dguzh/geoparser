import shutil
import zipfile
from pathlib import Path
from typing import Any, Dict

import requests

from geoparser.gazetteer.installer.model import SourceConfig
from geoparser.gazetteer.installer.stages.base import Stage
from geoparser.gazetteer.installer.utils.progress import create_progress_bar


class AcquisitionStage(Stage):
    """
    Downloads and extracts source files.

    This stage handles fetching remote data files and extracting them
    if they are compressed archives. It includes intelligent caching
    to avoid re-downloading files that haven't changed.
    """

    # Network request timeout in seconds
    REQUEST_TIMEOUT = 30

    # Download chunk size in bytes (8KB)
    DOWNLOAD_CHUNK_SIZE = 8192

    def __init__(self, downloads_directory: Path):
        """
        Initialize the acquisition stage.

        Args:
            downloads_directory: Directory to store downloaded files
        """
        super().__init__(
            name="Acquisition",
            description="Download and extract source files",
        )
        self.downloads_directory = downloads_directory
        self.downloads_directory.mkdir(parents=True, exist_ok=True)

    def execute(self, source: SourceConfig, context: Dict[str, Any]) -> None:
        """
        Download and extract files for a source.

        Args:
            source: Source configuration
            context: Shared context (will be populated with 'file_path')
        """
        source_path = self._resolve_source_path(source)
        file_path = self._resolve_file_path(source, source_path)

        # Store file path in context for subsequent stages
        context["file_path"] = file_path

    def cleanup(self) -> None:
        """Remove all downloaded files and extracted contents."""
        if self.downloads_directory.exists():
            shutil.rmtree(self.downloads_directory)

    def _resolve_source_path(self, source: SourceConfig) -> Path:
        """
        Resolve the path to the source file or directory.

        For remote URLs, downloads the file. For local paths, validates
        the path exists.

        Args:
            source: Source configuration

        Returns:
            Path to the source file or directory

        Raises:
            FileNotFoundError: If local path does not exist
        """
        if source.url:
            return self._download_file(source)
        else:
            return self._validate_local_path(source)

    def _validate_local_path(self, source: SourceConfig) -> Path:
        """
        Validate that a local path exists.

        Args:
            source: Source configuration

        Returns:
            Path to the local file or directory

        Raises:
            FileNotFoundError: If the path does not exist
        """
        local_path = Path(source.path)

        if not local_path.exists():
            raise FileNotFoundError(f"Local path does not exist: {local_path}")

        return local_path

    def _download_file(self, source: SourceConfig) -> Path:
        """
        Download a file if needed.

        Checks if the file already exists and has the same size as the
        remote file. If so, skips downloading.

        Args:
            source: Source configuration

        Returns:
            Path to the downloaded file
        """
        url = source.url
        download_path = self.downloads_directory / Path(url).name

        if self._should_skip_download(url, download_path):
            return download_path

        return self._stream_download(url, download_path)

    def _should_skip_download(self, url: str, local_path: Path) -> bool:
        """
        Check if we can skip downloading by comparing file sizes.

        Args:
            url: Remote file URL
            local_path: Local file path

        Returns:
            True if download can be skipped, False otherwise
        """
        if not local_path.exists():
            return False

        try:
            response = requests.head(url, timeout=self.REQUEST_TIMEOUT)
            remote_size = int(response.headers.get("content-length", 0))
            local_size = local_path.stat().st_size

            return remote_size == local_size and remote_size != 0
        except (requests.RequestException, ValueError):
            # If HEAD request fails, proceed with download
            return False

    def _stream_download(self, url: str, download_path: Path) -> Path:
        """
        Stream download a file with progress tracking.

        Args:
            url: Remote file URL
            download_path: Local path to save the file

        Returns:
            Path to the downloaded file
        """
        with requests.get(url, stream=True, timeout=self.REQUEST_TIMEOUT) as response:
            response.raise_for_status()
            total_size = int(response.headers.get("content-length", 0))

            with open(download_path, "wb") as f:
                with create_progress_bar(
                    total_size,
                    f"Downloading {download_path.name}",
                    "B",
                ) as pbar:
                    for chunk in response.iter_content(
                        chunk_size=self.DOWNLOAD_CHUNK_SIZE
                    ):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))

        return download_path

    def _resolve_file_path(self, source: SourceConfig, source_path: Path) -> Path:
        """
        Resolve the file path from a source path.

        Handles multiple scenarios:
        - Directories: searches recursively for the target file
        - ZIP archives: extracts and searches for the target file
        - Raw files: verifies the filename matches the target

        Args:
            source: Source configuration
            source_path: Path to the source file or directory

        Returns:
            Path to the target file

        Raises:
            FileNotFoundError: If the target file cannot be found
        """
        target_filename = source.file

        # If it's a directory, search for the target file
        if source_path.is_dir():
            return self._find_target_file(source_path, target_filename)

        # If not a ZIP file, verify it's the target file
        if not zipfile.is_zipfile(source_path):
            if source_path.name == target_filename:
                return source_path
            raise FileNotFoundError(f"File '{target_filename}' not found")

        # Extract ZIP archive
        extraction_dir = source_path.parent / source_path.stem

        if self._should_skip_extraction(source_path, extraction_dir, target_filename):
            return self._find_target_file(extraction_dir, target_filename)

        return self._extract_zip(source_path, extraction_dir, target_filename)

    def _should_skip_extraction(
        self,
        archive_path: Path,
        extraction_dir: Path,
        target_filename: str,
    ) -> bool:
        """
        Check if extraction can be skipped.

        Only applies to archive files, not to local directories which
        are already "extracted".

        Args:
            archive_path: Path to the archive file
            extraction_dir: Directory where files are/will be extracted
            target_filename: Name of the target file

        Returns:
            True if extraction can be skipped, False otherwise
        """
        if not extraction_dir.exists():
            return False

        # For local directories (not downloaded archives), always skip extraction
        # since they're already in their final form
        if not archive_path.is_file():
            return True

        # Check if the extraction directory itself is the target
        if extraction_dir.name == target_filename:
            if archive_path.stat().st_mtime <= extraction_dir.stat().st_mtime:
                return True

        # Check if target file exists and is up-to-date
        target_path = self._find_target_file_quiet(extraction_dir, target_filename)
        if target_path:
            if archive_path.stat().st_mtime <= target_path.stat().st_mtime:
                return True

        return False

    def _extract_zip(
        self,
        archive_path: Path,
        extraction_dir: Path,
        target_filename: str,
    ) -> Path:
        """
        Extract a ZIP archive.

        Args:
            archive_path: Path to the ZIP file
            extraction_dir: Directory to extract files to
            target_filename: Name of the target file

        Returns:
            Path to the target file

        Raises:
            FileNotFoundError: If target file not found in archive
        """
        # Remove old extraction if it exists
        if extraction_dir.exists():
            shutil.rmtree(extraction_dir)

        extraction_dir.mkdir(exist_ok=True)

        with zipfile.ZipFile(archive_path, "r") as zip_ref:
            # Calculate total size for progress tracking
            total_size = sum(info.file_size for info in zip_ref.infolist())

            with create_progress_bar(
                total_size,
                f"Extracting {archive_path.name}",
                "B",
            ) as pbar:
                for zip_info in zip_ref.infolist():
                    zip_ref.extract(zip_info, path=extraction_dir)
                    pbar.update(zip_info.file_size)

        # Check if extraction directory is the target
        if extraction_dir.name == target_filename:
            return extraction_dir

        # Find target file in extracted contents
        return self._find_target_file(extraction_dir, target_filename)

    def _find_target_file(self, directory: Path, filename: str) -> Path:
        """
        Find a file by name in a directory tree.

        Args:
            directory: Directory to search
            filename: Name of the file to find

        Returns:
            Path to the target file

        Raises:
            FileNotFoundError: If the file cannot be found
        """
        for path in directory.glob("**/*"):
            if path.name == filename:
                return path

        raise FileNotFoundError(f"File '{filename}' not found in archive")

    def _find_target_file_quiet(self, directory: Path, filename: str) -> Path:
        """
        Find a file by name, returning None if not found.

        Args:
            directory: Directory to search
            filename: Name of the file to find

        Returns:
            Path to the target file, or None if not found
        """
        try:
            return self._find_target_file(directory, filename)
        except FileNotFoundError:
            return None
