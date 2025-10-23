"""
Module fixtures for testing recognizers and resolvers.

Provides both mock and real module fixtures for unit and integration testing.
Mock fixtures are lightweight and fast for unit tests, while real fixtures
load actual models for integration tests.
"""

from typing import List, Tuple
from unittest.mock import Mock

import pytest

from geoparser.modules.recognizers.manual import ManualRecognizer
from geoparser.modules.recognizers.spacy import SpacyRecognizer
from geoparser.modules.resolvers.manual import ManualResolver
from geoparser.modules.resolvers.sentencetransformer import (
    SentenceTransformerResolver,
)

# Mock Recognizers for Unit Tests


@pytest.fixture
def mock_spacy_recognizer():
    """
    Create a mock SpacyRecognizer for unit tests.

    The mock has the same interface as the real recognizer but doesn't
    load spaCy models. Useful for testing service layer logic without
    the overhead of loading ML models.

    Returns:
        Mock SpacyRecognizer instance
    """
    mock_recognizer = Mock(spec=SpacyRecognizer)
    mock_recognizer.id = "mock_rec"
    mock_recognizer.name = "SpacyRecognizer"
    mock_recognizer.config = {"model_name": "en_core_web_sm", "entity_types": ["GPE"]}
    mock_recognizer.predict = Mock(return_value=[])
    return mock_recognizer


@pytest.fixture
def mock_manual_recognizer():
    """
    Create a mock ManualRecognizer for unit tests.

    Returns:
        Mock ManualRecognizer instance
    """
    mock_recognizer = Mock(spec=ManualRecognizer)
    mock_recognizer.id = "mock_man_rec"
    mock_recognizer.name = "ManualRecognizer"
    mock_recognizer.config = {"label": "test"}
    mock_recognizer.predict = Mock(return_value=[])
    return mock_recognizer


# Real Recognizers for Integration Tests


@pytest.fixture(scope="session")
def real_spacy_recognizer():
    """
    Create a real SpacyRecognizer with actual spaCy model.

    This fixture is session-scoped because loading the spaCy model is expensive.
    The model is loaded once and reused across all integration tests.

    Returns:
        SpacyRecognizer instance with loaded model
    """
    return SpacyRecognizer(model_name="en_core_web_sm", entity_types=["GPE", "LOC"])


@pytest.fixture
def real_manual_recognizer():
    """
    Create a real ManualRecognizer with test data.

    Returns:
        ManualRecognizer instance with sample annotations
    """
    texts = ["Test text with toponym"]
    references = [[(15, 22)]]  # "toponym"
    return ManualRecognizer(label="test", texts=texts, references=references)


# Mock Resolvers for Unit Tests


@pytest.fixture
def mock_sentencetransformer_resolver():
    """
    Create a mock SentenceTransformerResolver for unit tests.

    The mock has the same interface as the real resolver but doesn't
    load transformer models. Useful for testing service layer logic.

    Returns:
        Mock SentenceTransformerResolver instance
    """
    mock_resolver = Mock(spec=SentenceTransformerResolver)
    mock_resolver.id = "mock_res"
    mock_resolver.name = "SentenceTransformerResolver"
    mock_resolver.config = {
        "model_name": "dguzh/geo-all-MiniLM-L6-v2",
        "gazetteer_name": "geonames",
        "min_similarity": 0.7,
        "max_iter": 3,
    }
    mock_resolver.predict = Mock(return_value=[])
    return mock_resolver


@pytest.fixture
def mock_manual_resolver():
    """
    Create a mock ManualResolver for unit tests.

    Returns:
        Mock ManualResolver instance
    """
    mock_resolver = Mock(spec=ManualResolver)
    mock_resolver.id = "mock_man_res"
    mock_resolver.name = "ManualResolver"
    mock_resolver.config = {"label": "test"}
    mock_resolver.predict = Mock(return_value=[])
    return mock_resolver


# Real Resolvers for Integration Tests


@pytest.fixture(scope="session")
def real_sentencetransformer_resolver():
    """
    Create a real SentenceTransformerResolver with actual transformer model.

    This fixture is session-scoped because loading the transformer model is expensive.
    The model is loaded once and reused across all integration tests.

    Note: Uses a small model for faster testing. Integration tests should use
    the Andorra gazetteer for realistic candidate generation.

    Returns:
        SentenceTransformerResolver instance with loaded model
    """
    # Use a small model for faster testing
    return SentenceTransformerResolver(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        gazetteer_name="andorranames",
        min_similarity=0.5,
        max_iter=2,
    )


@pytest.fixture
def real_manual_resolver():
    """
    Create a real ManualResolver with test data.

    Returns:
        ManualResolver instance with sample annotations
    """
    texts = ["Test text"]
    references = [[(0, 4)]]
    referents = [[("geonames", "123")]]
    return ManualResolver(
        label="test", texts=texts, references=references, referents=referents
    )


# Helper fixtures for creating test module instances


@pytest.fixture
def create_manual_recognizer():
    """
    Factory fixture for creating ManualRecognizer instances.

    Returns:
        Function that creates ManualRecognizer with custom data
    """

    def _create(
        label: str, texts: List[str], references: List[List[Tuple[int, int]]]
    ) -> ManualRecognizer:
        return ManualRecognizer(label=label, texts=texts, references=references)

    return _create


@pytest.fixture
def create_manual_resolver():
    """
    Factory fixture for creating ManualResolver instances.

    Returns:
        Function that creates ManualResolver with custom data
    """

    def _create(
        label: str,
        texts: List[str],
        references: List[List[Tuple[int, int]]],
        referents: List[List[Tuple[str, str]]],
    ) -> ManualResolver:
        return ManualResolver(
            label=label, texts=texts, references=references, referents=referents
        )

    return _create
