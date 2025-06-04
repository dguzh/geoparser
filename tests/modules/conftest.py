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
    module.predict_references.return_value = [[(29, 35), (41, 46)]]
    return module


@pytest.fixture
def mock_resolution_module():
    """Create a mock resolution module for testing."""
    module = MagicMock(spec=AbstractResolutionModule)
    module.name = "mock_resolution"
    module.config = {"param": "value"}
    module.predict_referents.return_value = [
        [("test_gazetteer", "loc1"), ("test_gazetteer", "loc2")]
    ]
    return module
