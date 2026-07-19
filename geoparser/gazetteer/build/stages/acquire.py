"""
Acquisition of gazetteer source files.

Handles downloading remote files (with size-based caching), validating local
paths, extracting ZIP archives and locating the target file within extracted
contents or directories.
"""

import shutil
import zipfile
from pathlib import Path
from typing import Optional

import requests

from geoparser.gazetteer.build.progress import advance, item
from geoparser.gazetteer.build.schema import SourceConfig

# Network request timeout in seconds
REQUEST_TIMEOUT = 30

# Download chunk size in bytes (8KB)
DOWNLOAD_CHUNK_SIZE = 8192


class Acquirer:
    """
    Downloads and extracts gazetteer source files.

    Remote files are cached in the downloads directory and skipped when the
    local copy matches the remote size. ZIP archives are extracted next to
    the archive, with extraction skipped when contents are up to date. Each
    download or extraction that actually runs shows its own item bar and
    advances the active stage (see :mod:`progress`) once it finishes; a
    cached, unzipped local file shows neither and advances nothing.
    """

    def __init__(self, downloads_directory: Path):
        """
        Initialize the acquirer.

        Args:
            downloads_directory: Directory to store downloaded files
        """
        self.downloads_directory = downloads_directory
        self.downloads_directory.mkdir(parents=True, exist_ok=True)

    def acquire(self, source_config: SourceConfig) -> Path:
        """
        Resolve the data file for a source, downloading and extracting as needed.

        Args:
            source_config: Source configuration

        Returns:
            Path to the source's target file
        """
        source_path = self._resolve_source_path(source_config)
        return self._resolve_file_path(source_config, source_path)

    def cleanup(self) -> None:
        """Remove all downloaded files and extracted contents."""
        if self.downloads_directory.exists():
            shutil.rmtree(self.downloads_directory)

    def _resolve_source_path(self, source_config: SourceConfig) -> Path:
        """Download the source's file or validate its local path."""
        if source_config.url:
            return self._download_file(source_config.url)
        local_path = Path(source_config.path)
        if not local_path.exists():
            raise FileNotFoundError(f"Local path does not exist: {local_path}")
        return local_path

    def _download_file(self, url: str) -> Path:
        """Download a file unless a matching local copy already exists."""
        download_path = self.downloads_directory / Path(url).name
        if self._should_skip_download(url, download_path):
            return download_path
        return self._stream_download(url, download_path)

    def _should_skip_download(self, url: str, local_path: Path) -> bool:
        """Check if downloading can be skipped by comparing file sizes."""
        if not local_path.exists():
            return False
        try:
            response = requests.head(url, timeout=REQUEST_TIMEOUT)
            remote_size = int(response.headers.get("content-length", 0))
            local_size = local_path.stat().st_size
            return remote_size == local_size and remote_size != 0
        except (requests.RequestException, ValueError):
            # If the HEAD request fails, proceed with the download
            return False

    def _stream_download(self, url: str, download_path: Path) -> Path:
        """Stream a file download with progress tracking."""
        with requests.get(url, stream=True, timeout=REQUEST_TIMEOUT) as response:
            response.raise_for_status()
            total_size = int(response.headers.get("content-length", 0))

            with open(download_path, "wb") as output_file:
                with item(
                    f"Downloading {download_path.name}", total=total_size or None
                ) as progress_bar:
                    for chunk in response.iter_content(chunk_size=DOWNLOAD_CHUNK_SIZE):
                        if chunk:
                            output_file.write(chunk)
                            progress_bar.update(len(chunk))
        advance()

        return download_path

    def _resolve_file_path(
        self, source_config: SourceConfig, source_path: Path
    ) -> Path:
        """
        Locate the target file from a source path.

        Handles directories (recursive search), ZIP archives (extraction) and
        raw files (name check).
        """
        target_filename = source_config.file

        if source_path.is_dir():
            return self._find_target_file(source_path, target_filename)

        if not zipfile.is_zipfile(source_path):
            if source_path.name == target_filename:
                return source_path
            raise FileNotFoundError(
                f"Source '{source_config.name}': file '{target_filename}' not "
                f"found at {source_path}"
            )

        extraction_dir = source_path.parent / source_path.stem
        if self._should_skip_extraction(source_path, extraction_dir, target_filename):
            return self._find_target_file(extraction_dir, target_filename)
        return self._extract_zip(source_path, extraction_dir, target_filename)

    def _should_skip_extraction(
        self, archive_path: Path, extraction_dir: Path, target_filename: str
    ) -> bool:
        """Check if a previous extraction is still up to date."""
        if not extraction_dir.exists():
            return False

        # Local directories are already in their final form
        if not archive_path.is_file():
            return True

        if extraction_dir.name == target_filename:
            if archive_path.stat().st_mtime <= extraction_dir.stat().st_mtime:
                return True

        target_path = self._find_target_file_quiet(extraction_dir, target_filename)
        if target_path:
            if archive_path.stat().st_mtime <= target_path.stat().st_mtime:
                return True

        return False

    def _extract_zip(
        self, archive_path: Path, extraction_dir: Path, target_filename: str
    ) -> Path:
        """Extract a ZIP archive and locate the target file."""
        if extraction_dir.exists():
            shutil.rmtree(extraction_dir)
        extraction_dir.mkdir(exist_ok=True)

        with zipfile.ZipFile(archive_path, "r") as zip_ref:
            total_size = sum(info.file_size for info in zip_ref.infolist())
            with item(
                f"Unpacking {archive_path.name}", total=total_size or None
            ) as progress_bar:
                for zip_info in zip_ref.infolist():
                    zip_ref.extract(zip_info, path=extraction_dir)
                    progress_bar.update(zip_info.file_size)
        advance()

        if extraction_dir.name == target_filename:
            return extraction_dir
        return self._find_target_file(extraction_dir, target_filename)

    def _find_target_file(self, directory: Path, filename: str) -> Path:
        """Find a file by name in a directory tree."""
        for path in directory.glob("**/*"):
            if path.name == filename:
                return path
        raise FileNotFoundError(f"File '{filename}' not found in {directory}")

    def _find_target_file_quiet(
        self, directory: Path, filename: str
    ) -> Optional[Path]:
        """Find a file by name, returning None if not found."""
        try:
            return self._find_target_file(directory, filename)
        except FileNotFoundError:
            return None
