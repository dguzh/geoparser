"""
Tests for the text the resolver embeds on behalf of a candidate.

A candidate is compared to a reference's context as a sentence built from its
gazetteer attributes. The exact wording is what the encoder sees, so the
separators are behaviour rather than presentation.
"""

from unittest.mock import Mock, patch

import pytest


@pytest.fixture
def resolver():
    """A resolver using the geonames attribute map."""
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

        return SentenceTransformerResolver(gazetteer_name="geonames")


def _candidate(**data) -> Mock:
    """A gazetteer candidate carrying the given attributes."""
    candidate = Mock()
    candidate.data = data
    return candidate


@pytest.mark.unit
class TestGenerateDescription:
    """Turning a candidate's attributes into a sentence."""

    def test_names_the_place_its_type_and_its_administrative_context(self, resolver):
        """The full form reads as one sentence, most specific level first."""
        # Arrange
        candidate = _candidate(
            name="Paris",
            feature_name="city",
            admin2_name="Ile-de-France",
            admin1_name="IDF",
            country_name="France",
        )

        # Act & Assert
        assert (
            resolver._generate_description(candidate)
            == "Paris (city) in Ile-de-France, IDF, France"
        )

    def test_omits_the_type_when_the_candidate_has_none(self, resolver):
        """A candidate without a feature type still reads correctly."""
        # Arrange
        candidate = _candidate(name="Paris", country_name="France")

        # Act & Assert
        assert resolver._generate_description(candidate) == "Paris in France"

    def test_omits_the_administrative_context_when_there_is_none(self, resolver):
        """With no admin levels there is no trailing "in"."""
        # Arrange
        candidate = _candidate(name="Paris", feature_name="city")

        # Act & Assert
        assert resolver._generate_description(candidate) == "Paris (city)"

    def test_skips_empty_administrative_levels(self, resolver):
        """Blank levels are left out rather than producing empty separators."""
        # Arrange
        candidate = _candidate(name="Paris", admin2_name="", country_name="France")

        # Act & Assert
        assert resolver._generate_description(candidate) == "Paris in France"

    def test_describes_a_candidate_with_no_usable_attributes_as_empty(self, resolver):
        """
        Nothing known means nothing to embed.

        The annotator has its own description helper that falls back to the
        identifier; the resolver deliberately does not, so an attribute-less
        candidate contributes an empty string rather than a bare number.
        """
        # Arrange
        candidate = _candidate()

        # Act & Assert
        assert resolver._generate_description(candidate) == ""


@pytest.mark.unit
class TestAdminLevels:
    """Ordering the administrative names."""

    def test_returns_levels_from_most_to_least_specific(self, resolver):
        """level3, then level2, then level1."""
        # Act
        levels = resolver._admin_levels(
            {"admin2_name": "A2", "admin1_name": "A1", "country_name": "France"}
        )

        # Assert
        assert levels == ["A2", "A1", "France"]

    def test_returns_nothing_when_no_level_is_populated(self, resolver):
        """Missing levels yield an empty list, not blanks."""
        # Act & Assert
        assert resolver._admin_levels({}) == []


@pytest.mark.unit
class TestEmbeddingCaches:
    """Embedding candidates and contexts once each."""

    def test_describes_and_encodes_each_pending_candidate(self, resolver):
        """The descriptions handed to the encoder are the candidates' own."""
        # Arrange
        first, second = Mock(id=1), Mock(id=2)
        resolver.candidate_embeddings = {}
        with (
            patch.object(
                resolver,
                "_generate_description",
                side_effect=lambda c: f"desc-{c.id}",
            ),
            patch.object(resolver, "_encode", return_value=["e1", "e2"]) as encode,
        ):
            # Act
            resolver._embed_candidates([[[first, second]]], [[None]])

        # Assert
        assert encode.call_args.args[0] == ["desc-1", "desc-2"]
        assert resolver.candidate_embeddings == {1: "e1", 2: "e2"}

    def test_does_not_call_the_encoder_when_nothing_is_pending(self, resolver):
        """Already-embedded candidates cost nothing."""
        # Arrange
        candidate = Mock(id=1)
        resolver.candidate_embeddings = {1: "cached"}
        with patch.object(resolver, "_encode") as encode:
            # Act
            resolver._embed_candidates([[[candidate]]], [[None]])

        # Assert
        encode.assert_not_called()

    def test_caches_context_embeddings_by_their_text(self, resolver):
        """Each distinct context is encoded once and stored under itself."""
        # Arrange
        resolver.context_embeddings = {}
        with patch.object(resolver, "_encode", return_value=["ea", "eb"]) as encode:
            # Act
            resolver._embed_contexts([["b", "a"], ["a"]])

        # Assert - sorted, so the order is stable run to run
        assert encode.call_args.args[0] == ["a", "b"]
        assert resolver.context_embeddings == {"a": "ea", "b": "eb"}
