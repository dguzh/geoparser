"""
Tests for the contrastive pairs the resolver builds for fine-tuning.

Every candidate a reference could resolve to becomes a training pair: the
reference's context against that candidate's description, labelled 1 for the
referent that was actually chosen and 0 for the rest. Mislabelling or
misaligning those pairs trains the model on the wrong answer while still
producing a plausible-looking dataset.
"""

from unittest.mock import Mock, patch

import pytest


@pytest.fixture
def resolver():
    """A resolver with the gazetteer and models stubbed out."""
    with (
        patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer"),
        patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer"),
        patch(
            "geoparser.modules.resolvers.sentencetransformer.AutoTokenizer.from_pretrained"
        ),
        patch("geoparser.modules.resolvers.sentencetransformer.spacy.load"),
    ):
        from geoparser.modules.resolvers.sentencetransformer import (
            SentenceTransformerResolver,
        )

        return SentenceTransformerResolver()


def _candidate(identifier: str) -> Mock:
    """A gazetteer candidate with a stable description."""
    candidate = Mock(identifier=identifier)
    candidate.data = {}
    return candidate


@pytest.mark.unit
class TestPrepareTrainingData:
    """Building sentence1/sentence2/label triples."""

    @staticmethod
    def _prepare(resolver, texts, references, referents, candidates):
        """Run the builder with context and description generation stubbed."""
        resolver.gazetteer.search = Mock(return_value=candidates)
        with (
            patch.object(
                resolver,
                "_extract_context",
                side_effect=lambda text, start, end: f"ctx[{text[start:end]}]",
            ),
            patch.object(
                resolver,
                "_generate_description",
                side_effect=lambda c: f"desc[{c.identifier}]",
            ),
        ):
            return resolver._prepare_training_data(texts, references, referents)

    def test_labels_the_chosen_referent_positive_and_the_rest_negative(self, resolver):
        """Exactly the candidate that was resolved to gets label 1."""
        # Arrange
        candidates = [_candidate("1"), _candidate("2"), _candidate("3")]

        # Act
        data = self._prepare(
            resolver, ["Paris"], [[(0, 5)]], [[("geonames", "2")]], candidates
        )

        # Assert
        assert data["sentence2"] == ["desc[1]", "desc[2]", "desc[3]"]
        assert data["label"] == [0, 1, 0]

    def test_pairs_every_candidate_with_the_references_own_context(self, resolver):
        """sentence1 repeats the context once per candidate."""
        # Arrange
        candidates = [_candidate("1"), _candidate("2")]

        # Act
        data = self._prepare(
            resolver, ["Paris"], [[(0, 5)]], [[("geonames", "1")]], candidates
        )

        # Assert
        assert data["sentence1"] == ["ctx[Paris]", "ctx[Paris]"]

    def test_extracts_the_context_from_the_documents_own_text(self, resolver):
        """Each reference is contextualised against the document it came from."""
        # Arrange
        candidates = [_candidate("1")]

        # Act
        data = self._prepare(
            resolver,
            ["Paris and Berlin"],
            [[(0, 5), (10, 16)]],
            [[("geonames", "1"), ("geonames", "9")]],
            candidates,
        )

        # Assert
        assert data["sentence1"] == ["ctx[Paris]", "ctx[Berlin]"]

    def test_searches_the_gazetteer_for_the_reference_text(self, resolver):
        """Negative examples come from candidates for the reference itself."""
        # Arrange
        resolver.gazetteer.search = Mock(return_value=[])
        with (
            patch.object(resolver, "_extract_context", return_value="ctx"),
            patch.object(resolver, "_generate_description", return_value="desc"),
        ):
            # Act
            resolver._prepare_training_data(
                ["Paris and Berlin"],
                [[(0, 5), (10, 16)]],
                [[("geonames", "1"), ("geonames", "2")]],
            )

        # Assert
        assert [c.args[0] for c in resolver.gazetteer.search.call_args_list] == [
            "Paris",
            "Berlin",
        ]

    def test_produces_no_pairs_when_a_reference_has_no_candidates(self, resolver):
        """Nothing to contrast against means no training rows."""
        # Act
        data = self._prepare(resolver, ["Paris"], [[(0, 5)]], [[("geonames", "1")]], [])

        # Assert
        assert data == {"sentence1": [], "sentence2": [], "label": []}

    def test_rejects_documents_and_annotations_of_different_lengths(self, resolver):
        """
        The three per-document lists must line up.

        Zipping leniently would train on whichever prefix happened to match
        rather than reporting that the caller's data disagrees.
        """
        # Act & Assert
        with pytest.raises(ValueError):
            self._prepare(resolver, ["a", "b"], [[(0, 1)]], [[("g", "1")]], [])

    def test_rejects_references_and_referents_of_different_lengths(self, resolver):
        """The same applies within one document."""
        # Act & Assert
        with pytest.raises(ValueError):
            self._prepare(resolver, ["ab"], [[(0, 1), (1, 2)]], [[("g", "1")]], [])
