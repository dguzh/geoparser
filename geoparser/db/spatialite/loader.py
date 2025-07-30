import os
import platform
import sys
from pathlib import Path
from typing import Optional


def get_spatialite_path() -> Optional[Path]:
    """Get the path to the appropriate spatialite library for the current platform."""
    system = platform.system().lower()
    machine = platform.machine().lower()

    # Map platform.machine() outputs to our directory structure
    if machine in ("x86_64", "amd64"):
        arch = "x86_64" if system != "windows" else "amd64"
    elif machine in ("arm64", "aarch64"):
        # Only support ARM64 on macOS (Apple Silicon)
        if system == "darwin":
            arch = "arm64"
        else:
            # Linux ARM64 not supported - return None
            return None
    else:
        return None

    # Determine platform-specific directory and filename
    if system == "linux":
        platform_dir = f"linux-{arch}"
        filename = "mod_spatialite.so"
    elif system == "darwin":
        platform_dir = f"darwin-{arch}"
        filename = "mod_spatialite.dylib"
    elif system == "windows":
        platform_dir = f"win-{arch}"
        filename = "mod_spatialite.dll"
    else:
        return None

    # Get the path to the spatialite library
    spatialite_dir = Path(__file__).parent / platform_dir
    spatialite_path = spatialite_dir / filename

    return spatialite_path if spatialite_path.exists() else None


def load_spatialite_extension(dbapi_connection, spatialite_path: Path):
    """Load the SpatiaLite extension into a database connection."""
    try:
        # Enable extension loading
        dbapi_connection.enable_load_extension(True)

        # On Windows, add the directory containing the DLLs to the search path
        if platform.system() == "Windows" and sys.version_info >= (3, 8):
            with os.add_dll_directory(spatialite_path.parent):
                # Load the spatialite extension (without file extension)
                dbapi_connection.load_extension(str(spatialite_path.with_suffix("")))
        else:
            # Load the spatialite extension (without file extension)
            dbapi_connection.load_extension(str(spatialite_path.with_suffix("")))

        # Initialize spatial metadata only if it doesn't exist
        cursor = dbapi_connection.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='spatial_ref_sys'"
        )
        if not cursor.fetchone():
            cursor.execute("SELECT InitSpatialMetaData()")
        cursor.close()

    finally:
        # Always disable extension loading for security
        try:
            dbapi_connection.enable_load_extension(False)
        except Exception:
            pass  # Ignore errors when disabling
