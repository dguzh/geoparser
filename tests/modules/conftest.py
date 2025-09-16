# Shared fixtures across all module tests.
# Individual module types have their own conftest.py files in their respective directories.

import pytest

from geoparser.modules.module import Module


@pytest.fixture
def concrete_test_module_class():
    """Create a concrete subclass of Module for testing."""

    class TestModule(Module):
        NAME = "test_module"

    return TestModule
