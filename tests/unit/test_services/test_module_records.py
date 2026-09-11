"""
Tests for the module rows the services write before recording predictions.

A module's row carries the configuration it ran with. Predictions are keyed by
the module id, so a row that records the id but loses the config leaves no way
to tell later what actually produced the annotations -- and the loss is
invisible at prediction time.
"""

import pytest
from sqlmodel import select

from geoparser.db.db import get_session
from geoparser.db.models import Recognizer, Resolver
from geoparser.services.recognition import RecognitionService
from geoparser.services.resolution import ResolutionService


class _Module:
    """A stand-in module with a fixed id, name and config."""

    def __init__(self, name, config):
        self.id = f"{name}-id"
        self.name = name
        self.config = config


@pytest.mark.unit
class TestRecognizerRecord:
    """The row RecognitionService writes for its recognizer."""

    def test_stores_the_recognizers_name_and_config(self):
        """Everything the recognizer was configured with is persisted."""
        # Arrange
        recognizer = _Module("SpacyRecognizer", {"model_name": "en_core_web_sm"})
        service = RecognitionService(recognizer)

        # Act
        recognizer_id = service._ensure_recognizer_record(recognizer)

        # Assert
        with get_session() as session:
            rows = session.exec(select(Recognizer)).all()
        assert recognizer_id == "SpacyRecognizer-id"
        assert [(row.name, row.config) for row in rows] == [
            ("SpacyRecognizer", {"model_name": "en_core_web_sm"})
        ]

    def test_reuses_an_existing_row_rather_than_writing_a_second(self):
        """The same recognizer twice is one row."""
        # Arrange
        recognizer = _Module("SpacyRecognizer", {"model_name": "en_core_web_sm"})
        service = RecognitionService(recognizer)

        # Act
        service._ensure_recognizer_record(recognizer)
        service._ensure_recognizer_record(recognizer)

        # Assert
        with get_session() as session:
            assert len(session.exec(select(Recognizer)).all()) == 1


@pytest.mark.unit
class TestResolverRecord:
    """The row ResolutionService writes for its resolver."""

    def test_stores_the_resolvers_name_and_config(self):
        """Everything the resolver was configured with is persisted."""
        # Arrange
        resolver = _Module("SentenceTransformerResolver", {"min_similarity": 0.6})
        service = ResolutionService(resolver)

        # Act
        resolver_id = service._ensure_resolver_record(resolver)

        # Assert
        with get_session() as session:
            rows = session.exec(select(Resolver)).all()
        assert resolver_id == "SentenceTransformerResolver-id"
        assert [(row.name, row.config) for row in rows] == [
            ("SentenceTransformerResolver", {"min_similarity": 0.6})
        ]

    def test_reuses_an_existing_row_rather_than_writing_a_second(self):
        """The same resolver twice is one row."""
        # Arrange
        resolver = _Module("SentenceTransformerResolver", {"min_similarity": 0.6})
        service = ResolutionService(resolver)

        # Act
        service._ensure_resolver_record(resolver)
        service._ensure_resolver_record(resolver)

        # Assert
        with get_session() as session:
            assert len(session.exec(select(Resolver)).all()) == 1
