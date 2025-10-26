"""
Gazetteer fixtures for testing.

Provides fixtures for working with the Andorra gazetteer in tests,
including paths to configuration files and a helper to install the gazetteer.
"""

from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def andorra_config_path() -> Path:
    """
    Get the path to the Andorra gazetteer configuration file.

    Returns:
        Path to andorranames.yaml configuration file
    """
    return Path(__file__).parent / "gazetteer" / "andorranames.yaml"


@pytest.fixture(scope="function")
def andorra_gazetteer(andorra_config_path: Path) -> None:
    """
    Install the Andorra gazetteer into the test database.

    This fixture automatically installs the Andorra gazetteer for tests that need it.
    The autouse patch_get_engine fixture ensures that get_engine() returns the test
    database, so the installer will use the test database automatically.

    Args:
        andorra_config_path: Path to andorranames.yaml configuration file
    """
    from geoparser.gazetteer.installer import GazetteerInstaller

    installer = GazetteerInstaller()
    installer.install(andorra_config_path, chunksize=5000, keep_downloads=False)
