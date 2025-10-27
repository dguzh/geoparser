"""
Root conftest.py for geoparser test suite.

This module provides pytest configuration and imports all fixtures
from the fixtures directory, making them available to all tests.
"""

# Import all fixtures from the fixtures directory
# This makes them available to all tests without explicit imports
pytest_plugins = [
    "tests.fixtures.db",
    "tests.fixtures.models",
    "tests.fixtures.modules",
    "tests.fixtures.gazetteer",
]


def pytest_configure(config):
    """
    Configure pytest with custom settings.

    Args:
        config: Pytest config object
    """
    # Add custom markers (already defined in pytest.ini, but can be extended here)
    config.addinivalue_line("markers", "unit: Fast unit tests with mocked dependencies")
    config.addinivalue_line(
        "markers", "integration: Integration tests with real dependencies"
    )
    config.addinivalue_line("markers", "e2e: End-to-end pipeline tests")
