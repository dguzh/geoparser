from unittest.mock import MagicMock

import pytest

from geoparser.modules.interfaces import (
    AbstractRecognitionModule,
    AbstractResolutionModule,
)


@pytest.fixture
def mock_recognition_module():
    """Create a mock recognition module for testing."""
    module = MagicMock(spec=AbstractRecognitionModule)
    module.name = "mock_recognition"
    module.config = {"param": "value"}
    module.predict_toponyms.return_value = [[(27, 33), (39, 44)]]
    return module


@pytest.fixture
def mock_resolution_module():
    """Create a mock resolution module for testing."""
    module = MagicMock(spec=AbstractResolutionModule)
    module.name = "mock_resolution"
    module.config = {"param": "value"}
    module.predict_locations.return_value = [[("loc1", 0.8), ("loc2", 0.6)]]
    return module
