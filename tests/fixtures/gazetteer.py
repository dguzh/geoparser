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


def install_andorra_gazetteer(engine: Engine, config_path: Path) -> None:
    """
    Install the Andorra gazetteer into the given database engine.

    This helper function patches the global engine to use the provided test engine,
    then installs the Andorra gazetteer.

    Use this in integration tests that need gazetteer data.

    Args:
        engine: SQLAlchemy Engine instance to install gazetteer into
        config_path: Path to andorranames.yaml configuration file
    """
    from geoparser.gazetteer.installer import GazetteerInstaller

    # Patch the single source of truth for the engine
    with patch("geoparser.db.engine.engine", engine):
        installer = GazetteerInstaller()
        installer.install(config_path, chunksize=5000, keep_downloads=False)
