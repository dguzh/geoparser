"""
Unit tests for geoparser/modules/resolvers/spanencoder.py

Tests span/token utilities and serialization with mocked heavy dependencies.
"""

from unittest.mock import Mock, patch

import pytest
import torch


def _make_resolver(**kwargs):
    from geoparser.modules.resolvers.spanencoder import SpanEncoderResolver

    with (
        patch("geoparser.modules.resolvers.spanencoder.AutoConfig"),
        patch("geoparser.modules.resolvers.spanencoder.AutoModel") as mock_model,
        patch("geoparser.modules.resolvers.spanencoder.AutoTokenizer"),
        patch("geoparser.modules.resolvers.spanencoder.Gazetteer"),
    ):
        mock_model.from_pretrained.return_value.config.hidden_size = 768
        mock_model.from_pretrained.return_value.to = Mock()
        return SpanEncoderResolver(**kwargs)


@pytest.mark.unit
class TestSpanEncoderResolverInitialization:
    def test_creates_with_default_parameters(self):
        resolver = _make_resolver()

        assert resolver.name == "SpanEncoderResolver"
        assert resolver.model_name == "answerdotai/ModernBERT-base"
        assert resolver.gazetteer_name == "geonames"
        assert resolver.min_similarity == 0.6
        assert resolver.max_tiers == 3
        assert resolver.embedding_dim == 256

    def test_unknown_gazetteer_without_map_raises(self):
        with pytest.raises(ValueError, match="not configured"):
            _make_resolver(gazetteer_name="unknown")

    def test_custom_attribute_map(self):
        custom_map = {"name": "n", "type": "t", "level1": "l1"}
        resolver = _make_resolver(
            gazetteer_name="custom", attribute_map=custom_map
        )

        assert resolver.attribute_map == custom_map


@pytest.mark.unit
class TestCharSpanToTokenSpan:
    def test_exact_alignment(self):
        from geoparser.modules.resolvers.spanencoder import SpanEncoderResolver

        # Tokens: [CLS] "Alexandria" "is" [SEP] with offsets
        offsets = [(0, 0), (0, 10), (11, 13), (0, 0)]

        assert SpanEncoderResolver._char_span_to_token_span(offsets, 0, 10) == (1, 1)

    def test_multi_token_span(self):
        from geoparser.modules.resolvers.spanencoder import SpanEncoderResolver

        offsets = [(0, 0), (0, 7), (8, 14), (15, 20), (0, 0)]

        assert SpanEncoderResolver._char_span_to_token_span(offsets, 0, 14) == (1, 2)

    def test_partial_overlap_included(self):
        from geoparser.modules.resolvers.spanencoder import SpanEncoderResolver

        # A token partially overlapping the char span is included
        offsets = [(0, 0), (0, 5), (5, 12), (0, 0)]

        assert SpanEncoderResolver._char_span_to_token_span(offsets, 3, 8) == (1, 2)

    def test_no_overlap_returns_none(self):
        from geoparser.modules.resolvers.spanencoder import SpanEncoderResolver

        offsets = [(0, 0), (0, 5), (0, 0)]

        assert SpanEncoderResolver._char_span_to_token_span(offsets, 10, 15) is None


@pytest.mark.unit
class TestSerializeCandidate:
    def test_full_attributes(self):
        resolver = _make_resolver()
        candidate = Mock()
        candidate.data = {
            "name": "Alexandria",
            "feature_name": "populated place",
            "country_name": "United States",
            "admin1_name": "Louisiana",
            "admin2_name": "Rapides Parish",
        }

        serialized, name = resolver._serialize_candidate(candidate)

        assert serialized == (
            "Alexandria | populated place | "
            "Rapides Parish > Louisiana > United States"
        )
        assert name == "Alexandria"

    def test_missing_attributes_are_skipped(self):
        resolver = _make_resolver()
        candidate = Mock()
        candidate.data = {"name": "Alexandria"}

        serialized, name = resolver._serialize_candidate(candidate)

        assert serialized == "Alexandria"
        assert name == "Alexandria"

    def test_partial_admin_hierarchy(self):
        resolver = _make_resolver()
        candidate = Mock()
        candidate.data = {
            "name": "Alexandria",
            "country_name": "Egypt",
        }

        serialized, _ = resolver._serialize_candidate(candidate)

        assert serialized == "Alexandria | Egypt"


@pytest.mark.unit
class TestMentionTokenWindow:
    def test_window_centered_on_mention(self):
        resolver = _make_resolver(max_context_tokens=4)
        input_ids = list(range(100, 112))  # 12 tokens
        offsets = [(i * 2, i * 2 + 2) for i in range(12)]

        window_ids, first, last = resolver._mention_token_window(
            input_ids, offsets, 12, 14, 4
        )

        assert len(window_ids) == 4
        # The mention token (index 6 overall) is inside the window
        assert window_ids[first] == 106
        assert first <= last < len(window_ids)

    def test_mention_not_found(self):
        resolver = _make_resolver()
        window_ids, first, last = resolver._mention_token_window(
            [1, 2, 3], [(0, 0), (0, 0), (0, 0)], 5, 8, 4
        )

        assert window_ids is None
        assert first is None
        assert last is None
