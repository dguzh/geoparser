"""
Gazetteer fixtures for testing.

Provides fixtures for working with the Andorra gazetteer in tests,
including paths to configuration files and a helper to install the gazetteer.
"""

from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import Engine


@pytest.fixture(scope="session")
def andorra_config_path() -> Path:
    """
    Get the path to the Andorra gazetteer configuration file.

    Returns:
        Path to andorranames.yaml configuration file
    """
    return Path(__file__).parent / "gazetteer" / "andorranames.yaml"


@pytest.fixture(scope="function")
def andorra_gazetteer(test_engine: Engine, andorra_config_path: Path) -> None:
    """
    Install the Andorra gazetteer into the test database.

    This fixture automatically installs the Andorra gazetteer for tests that need it.
    It uses the function-scoped test_engine fixture to ensure each test has its own
    isolated database with fresh gazetteer data.

    Args:
        test_engine: Function-scoped test database engine (from database fixtures)
        andorra_config_path: Path to andorranames.yaml configuration file
    """
    from geoparser.gazetteer.installer import GazetteerInstaller

    # Patch the engine getter to return our test engine
    with patch("geoparser.db.engine.get_engine", return_value=test_engine):
        installer = GazetteerInstaller()
        installer.install(andorra_config_path, chunksize=5000, keep_downloads=False)
