from unittest.mock import MagicMock

import pytest

from geoparser.modules.recognizers.base import Recognizer
from geoparser.modules.resolvers.base import Resolver


@pytest.fixture
def mock_recognizer():
    """Create a mock recognizer for testing."""
    recognizer = MagicMock(spec=Recognizer)
    recognizer.name = "mock_recognizer"
    recognizer.config = {"param": "value"}
    recognizer.predict_references.return_value = [[(29, 35), (41, 46)]]
    return recognizer


@pytest.fixture
def mock_resolver():
    """Create a mock resolver for testing."""
    resolver = MagicMock(spec=Resolver)
    resolver.name = "mock_resolver"
    resolver.config = {"param": "value"}
    resolver.predict_referents.return_value = [("test_gazetteer", "loc1")]
    return resolver
