"""
Tests for the data ResolutionService hands to a resolver.

The service's job when training is to line up three parallel lists -- texts,
reference spans and their referents -- and pass them on. Existing tests check
that fit is called; these check that it is called with the right data, since
swapping or dropping one of the lists trains on nonsense while still looking
like a successful call.
"""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from geoparser.services.resolution import ResolutionService


def _toponym(start: int, end: int, gazetteer: str | None = None, identifier: str = ""):
    """A reference, optionally resolved to a gazetteer feature."""
    location = (
        SimpleNamespace(gazetteer_name=gazetteer, identifier=identifier)
        if gazetteer
        else None
    )
    return SimpleNamespace(start=start, end=end, location=location)


def _document(text: str, toponyms: list) -> SimpleNamespace:
    """A document stub carrying only what the service reads."""
    return SimpleNamespace(text=text, toponyms=toponyms)


@pytest.mark.unit
class TestAnnotatedPairs:
    """Extracting one document's resolved toponyms."""

    def test_pairs_each_span_with_its_referent(self):
        """Spans and referents come back aligned, in document order."""
        # Arrange
        doc = _document(
            "Paris and Berlin",
            [_toponym(0, 5, "geonames", "1"), _toponym(10, 16, "geonames", "2")],
        )

        # Act
        spans, referents = ResolutionService._annotated_pairs(doc)

        # Assert
        assert spans == [(0, 5), (10, 16)]
        assert referents == [("geonames", "1"), ("geonames", "2")]

    def test_drops_toponyms_that_were_never_resolved(self):
        """An unresolved toponym contributes neither a span nor a referent."""
        # Arrange
        doc = _document(
            "Paris and Nowhere",
            [_toponym(0, 5, "geonames", "1"), _toponym(10, 17)],
        )

        # Act
        spans, referents = ResolutionService._annotated_pairs(doc)

        # Assert
        assert spans == [(0, 5)]
        assert referents == [("geonames", "1")]

    def test_returns_two_empty_lists_for_an_unannotated_document(self):
        """Nothing resolved means nothing to train on."""
        # Arrange
        doc = _document("Nothing here", [_toponym(0, 7)])

        # Act
        spans, referents = ResolutionService._annotated_pairs(doc)

        # Assert
        assert spans == []
        assert referents == []


@pytest.mark.unit
class TestFitDataFlow:
    """What reaches the resolver's own fit method."""

    @staticmethod
    def _service_with_resolver():
        """A service whose resolver records how fit was called."""
        resolver = Mock()
        resolver.name = "TestResolver"
        return ResolutionService(resolver), resolver

    def test_passes_texts_references_and_referents_in_step(self):
        """The three lists line up index for index."""
        # Arrange
        service, resolver = self._service_with_resolver()
        documents = [
            _document("Paris", [_toponym(0, 5, "geonames", "1")]),
            _document("Berlin", [_toponym(0, 6, "geonames", "2")]),
        ]

        # Act
        service.fit(documents)

        # Assert
        texts, references, referents = resolver.fit.call_args.args
        assert texts == ["Paris", "Berlin"]
        assert references == [[(0, 5)], [(0, 6)]]
        assert referents == [[("geonames", "1")], [("geonames", "2")]]

    def test_skips_documents_with_no_resolved_toponyms(self):
        """A document with nothing annotated is left out of training."""
        # Arrange
        service, resolver = self._service_with_resolver()
        documents = [
            _document("Paris", [_toponym(0, 5, "geonames", "1")]),
            _document("Unannotated", [_toponym(0, 5)]),
        ]

        # Act
        service.fit(documents)

        # Assert
        texts, references, referents = resolver.fit.call_args.args
        assert texts == ["Paris"]
        assert references == [[(0, 5)]]
        assert referents == [[("geonames", "1")]]

    def test_forwards_training_parameters(self):
        """Extra keyword arguments reach the resolver untouched."""
        # Arrange
        service, resolver = self._service_with_resolver()
        documents = [_document("Paris", [_toponym(0, 5, "geonames", "1")])]

        # Act
        service.fit(documents, epochs=7, output_path="/tmp/out")

        # Assert
        assert resolver.fit.call_args.kwargs == {"epochs": 7, "output_path": "/tmp/out"}

    def test_rejects_a_resolver_that_cannot_be_trained(self):
        """A resolver without a fit method is reported by name."""
        # Arrange
        resolver = SimpleNamespace(name="ManualResolver")
        service = ResolutionService(resolver)

        # Act & Assert
        with pytest.raises(ValueError, match="ManualResolver"):
            service.fit([_document("Paris", [_toponym(0, 5, "geonames", "1")])])
