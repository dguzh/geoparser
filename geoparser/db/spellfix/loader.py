import os
import platform
from pathlib import Path
from typing import Optional


def get_spellfix_path() -> Optional[Path]:
    """
    Get the path to the appropriate spellfix library for the current platform.

    Returns:
        Path to the spellfix library if found, None otherwise.
    """
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
        filename = "spellfix.so"
    elif system == "darwin":
        platform_dir = f"darwin-{arch}"
        filename = "spellfix.dylib"
    elif system == "windows":
        platform_dir = f"win-{arch}"
        filename = "spellfix.dll"
    else:
        return None

    # Get the path to the spellfix library
    spellfix_dir = Path(__file__).parent / platform_dir
    spellfix_path = spellfix_dir / filename

    return spellfix_path if spellfix_path.exists() else None


def load_spellfix_extension(dbapi_connection, spellfix_path: Path):
    """
    Load the Spellfix extension into a database connection.

    Args:
        dbapi_connection: SQLite database connection object.
        spellfix_path: Path to the Spellfix library file.
    """
    try:
        # Enable extension loading
        dbapi_connection.enable_load_extension(True)

        # On Windows, add the directory containing the DLL to the PATH
        if platform.system() == "Windows":
            original_path = os.environ.get("PATH", "")
            dll_dir = str(spellfix_path.parent)
            try:
                # Temporarily add the DLL directory to PATH
                os.environ["PATH"] = dll_dir + os.pathsep + original_path
                # Load the spellfix extension (without file extension)
                dbapi_connection.load_extension(str(spellfix_path.with_suffix("")))
            finally:
                # Restore original PATH
                os.environ["PATH"] = original_path
        else:
            # Load the spellfix extension (without file extension)
            dbapi_connection.load_extension(str(spellfix_path.with_suffix("")))

    finally:
        # Always disable extension loading for security
        try:
            dbapi_connection.enable_load_extension(False)
        except Exception:
            pass  # Ignore errors when disabling
