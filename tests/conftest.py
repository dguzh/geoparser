"""
Root conftest.py for geoparser test suite.

This module provides pytest configuration and imports all fixtures
from the fixtures directory, making them available to all tests.
"""

import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest

# Import all fixtures from the fixtures directory
# This makes them available to all tests without explicit imports
pytest_plugins = [
    "tests.fixtures.db",
    "tests.fixtures.models",
    "tests.fixtures.modules",
    "tests.fixtures.gazetteer",
]

_TRAINING_OUTPUT_NAMES = frozenset(
    {
        "initial_model",
        "model1",
        "model2",
        "trained_model",
        "trained_recognizer",
        "trained_resolver",
        "updated_model",
    }
)


def _cleanup_training_outputs(tmp_path: Path) -> None:
    """Remove large model outputs while retaining other test fixtures."""
    for path in tmp_path.iterdir():
        if path.name in _TRAINING_OUTPUT_NAMES and path.is_dir():
            shutil.rmtree(path)


@pytest.fixture(autouse=True)
def cleanup_training_outputs(tmp_path: Path) -> Iterator[None]:
    """Keep per-test model checkpoints from accumulating on disk."""
    yield
    _cleanup_training_outputs(tmp_path)


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
