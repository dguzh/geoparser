import shutil
import zipfile
from pathlib import Path

import requests
from tqdm.auto import tqdm

from geoparser.gazetteer.model import SourceConfig


class DataDownloader:
    """Handles downloading and extracting gazetteer data files."""

    # Default chunk size for streaming downloads (8KB)
    DEFAULT_CHUNK_SIZE = 8192
    # Default timeout for network requests (30 seconds)
    DEFAULT_TIMEOUT = 30

    def download(self, source_config: SourceConfig, downloads_dir: Path) -> Path:
        """
        Download a file if it doesn't exist or has changed size.

        Args:
            source_config: Source configuration
            downloads_dir: Directory to save the file in

        Returns:
            Path to the downloaded file
        """
        url = source_config.url
        download_path = downloads_dir / Path(url).name

        if download_path.exists():
            # Check if we need to re-download by comparing file size
            try:
                headers = requests.head(url, timeout=self.DEFAULT_TIMEOUT).headers
                remote_size = int(headers.get("content-length", 0))
                local_size = download_path.stat().st_size

                if remote_size == local_size and remote_size != 0:
                    return download_path
            except (requests.RequestException, ValueError):
                # If HEAD request fails, proceed with download anyway
                pass

        # Stream download with progress bar
        with requests.get(url, stream=True, timeout=self.DEFAULT_TIMEOUT) as r:
            r.raise_for_status()
            total_size = int(r.headers.get("content-length", 0))

            with open(download_path, "wb") as f:
                with tqdm(
                    total=total_size,
                    unit="B",
                    unit_scale=True,
                    desc=f"Downloading {download_path.name}",
                ) as pbar:
                    for chunk in r.iter_content(chunk_size=self.DEFAULT_CHUNK_SIZE):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))

        return download_path

    def extract(self, source_config: SourceConfig, download_path: Path) -> Path:
        """
        Extract files from a zip archive and locate the target file.

        For non-zip files, verifies the file exists and returns its path.
        For zip files, extracts contents and returns the path to the target file.

        Args:
            source_config: Source configuration
            download_path: Path to the downloaded file

        Returns:
            Path to the target file

        Raises:
            FileNotFoundError: If the target file can't be found
        """
        target_file = source_config.file

        # If not a zip file, check if it's the target file
        if not zipfile.is_zipfile(download_path):
            if download_path.name == target_file:
                return download_path
            else:
                raise FileNotFoundError(f"File '{target_file}' not found")

        # Create extraction directory
        extraction_dir = download_path.parent / download_path.stem

        # Check if already extracted and up to date
        if extraction_dir.exists():
            # Check if extraction directory itself is the target
            if extraction_dir.name == target_file:
                if download_path.stat().st_mtime <= extraction_dir.stat().st_mtime:
                    return extraction_dir

            # Check if target file exists in extraction directory
            for path in extraction_dir.glob("**/*"):
                if path.name == target_file:
                    if download_path.stat().st_mtime <= path.stat().st_mtime:
                        return path

            # Need to re-extract
            shutil.rmtree(extraction_dir)

        # Extract files
        extraction_dir.mkdir(exist_ok=True)

        with zipfile.ZipFile(download_path, "r") as zip_ref:
            # Calculate total size for progress tracking
            total_size = sum(file.file_size for file in zip_ref.infolist())

            with tqdm(
                total=total_size,
                unit="B",
                unit_scale=True,
                desc=f"Extracting {download_path.name}",
            ) as pbar:
                for zip_info in zip_ref.infolist():
                    zip_ref.extract(zip_info, path=extraction_dir)
                    pbar.update(zip_info.file_size)

        # Check if extraction directory is the target
        if extraction_dir.name == target_file:
            return extraction_dir

        # Look for target file in extracted contents
        for path in extraction_dir.glob("**/*"):
            if path.name == target_file:
                return path

        # Target file not found
        raise FileNotFoundError(f"File '{target_file}' not found in archive")

    def cleanup(self, downloads_dir: Path) -> None:
        """
        Clean up downloaded files and extracted contents.

        Args:
            downloads_dir: Path to the gazetteer directory to clean up
        """
        if downloads_dir.exists():
            shutil.rmtree(downloads_dir)
