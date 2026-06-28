import pytest


@pytest.fixture(autouse=True)
def _autouse_installed_geonames(installed_geonames):
    """Ensure geonames is installed for all tests in this directory."""
