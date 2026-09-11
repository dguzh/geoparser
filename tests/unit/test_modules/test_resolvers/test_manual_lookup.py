"""
Tests for how ManualResolver looks up stored annotations.

The resolver replays annotations recorded elsewhere, matching a document by
its text and a reference by its exact span. Anything it has no annotation for
comes back as None so the service leaves it unprocessed rather than recording
a wrong answer.
"""

import pytest

from geoparser.modules.resolvers.manual import ManualResolver


@pytest.fixture
def resolver():
    """A resolver holding annotations for two documents."""
    return ManualResolver(
        label="annotator_a",
        texts=["Paris and Berlin", "Rome"],
        references=[[(0, 5), (10, 16)], [(0, 4)]],
        referents=[[("geonames", "1"), None], [("geonames", "3")]],
    )


@pytest.mark.unit
class TestManualPredict:
    """Replaying stored referents."""

    def test_returns_the_referent_recorded_for_each_span(self, resolver):
        """A known document and span yields its stored referent."""
        # Act
        results = resolver.predict(["Rome"], [[(0, 4)]])

        # Assert
        assert results == [[("geonames", "3")]]

    def test_preserves_a_recorded_none_for_an_ungeocoded_span(self, resolver):
        """A span annotated as ungeocoded stays None."""
        # Act
        results = resolver.predict(["Paris and Berlin"], [[(0, 5), (10, 16)]])

        # Assert
        assert results == [[("geonames", "1"), None]]

    def test_returns_none_for_a_span_that_was_never_annotated(self, resolver):
        """An unknown span is not guessed at."""
        # Act
        results = resolver.predict(["Rome"], [[(1, 3)]])

        # Assert
        assert results == [[None]]

    def test_returns_none_for_every_span_of_an_unknown_document(self, resolver):
        """
        A document the annotator never saw yields one None per reference.

        The result still has to line up with the references asked about, or
        the service would pair referents with the wrong spans.
        """
        # Act
        results = resolver.predict(["Lisbon"], [[(0, 6), (7, 8)]])

        # Assert
        assert results == [[None, None]]

    def test_matches_documents_by_text_not_by_position(self, resolver):
        """Documents may be presented in any order."""
        # Act
        results = resolver.predict(["Rome", "Paris and Berlin"], [[(0, 4)], [(0, 5)]])

        # Assert
        assert results == [[("geonames", "3")], [("geonames", "1")]]

    def test_rejects_texts_and_references_of_different_lengths(self, resolver):
        """
        The caller's two lists must describe the same documents.

        Zipping them leniently would return fewer results than references
        asked about, and the service pairs the two by position.
        """
        # Act & Assert
        with pytest.raises(ValueError):
            resolver.predict(["Rome", "Paris and Berlin"], [[(0, 4)]])
