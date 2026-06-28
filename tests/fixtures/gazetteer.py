"""
Gazetteer fixtures for testing.

Provides fixtures for working with the Andorra gazetteer in tests,
including paths to configuration files and a helper to install the gazetteer.
"""

from datetime import datetime, timezone
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
    The autouse patch_db fixture redirects all database operations to use the test
    database, so the installer will use the test database automatically.

    Args:
        andorra_config_path: Path to andorranames.yaml configuration file
    """
    from geoparser.gazetteer.installer import GazetteerInstaller

    installer = GazetteerInstaller()
    installer.install(andorra_config_path, chunksize=5000, keep_downloads=False)


@pytest.fixture
def installed_geonames(test_session):
    """
    Register an installed "geonames" gazetteer in the test database.

    The Gazetteer guard rejects uninstalled gazetteers at construction, so unit
    tests that exercise search/find need a completed installation record.
    """
    from geoparser.db.models import Gazetteer as GazetteerModel

    gazetteer_record = GazetteerModel(
        name="geonames", installed_at=datetime.now(timezone.utc)
    )
    test_session.add(gazetteer_record)
    test_session.commit()
