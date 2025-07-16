import platform
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
