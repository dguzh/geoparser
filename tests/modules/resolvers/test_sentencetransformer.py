from unittest.mock import MagicMock, patch

import pytest
import torch

from geoparser.modules.resolvers.sentencetransformer import SentenceTransformerResolver


@pytest.fixture
def mock_references():
    """Create mock Reference objects for testing."""
    ref1 = MagicMock()
    ref1.id = 1
    ref1.text = "London"
    ref1.start = 10
    ref1.end = 16
    ref1.document.text = "I visited London last summer."

    ref2 = MagicMock()
    ref2.id = 2
    ref2.text = "Paris"
    ref2.start = 21
    ref2.end = 26
    ref2.document.text = "We went to Paris and London."

    return [ref1, ref2]


@pytest.fixture
def mock_features():
    """Create mock Feature objects for testing."""
    feature1 = MagicMock()
    feature1.id = 101
    feature1.identifier_value = "2643743"
    feature1.data = {
        "name": "London",
        "feature_name": "populated place",
        "country_name": "United Kingdom",
        "admin1_name": "England",
    }

    feature2 = MagicMock()
    feature2.id = 102
    feature2.identifier_value = "2988507"
    feature2.data = {
        "name": "Paris",
        "feature_name": "capital",
        "country_name": "France",
        "admin1_name": "Île-de-France",
    }

    return [feature1, feature2]


@pytest.fixture
def mock_sentence_transformer():
    """Create a mock SentenceTransformer."""
    mock_transformer = MagicMock()
    mock_transformer.get_max_seq_length.return_value = 512
    mock_transformer.encode.return_value = torch.randn(2, 384)  # Mock embeddings
    return mock_transformer


@pytest.fixture
def mock_tokenizer():
    """Create a mock tokenizer."""
    mock_tokenizer = MagicMock()
    mock_tokenizer.tokenize.return_value = ["token1", "token2", "token3"]  # Mock tokens
    return mock_tokenizer


@pytest.fixture
def mock_spacy_nlp():
    """Create a mock spaCy model."""
    mock_nlp = MagicMock()

    # Mock sentence
    mock_sent = MagicMock()
    mock_sent.start_char = 0
    mock_sent.end_char = 29
    mock_sent.text = "I visited London last summer."

    # Mock document with sentences
    mock_doc = MagicMock()
    mock_doc.sents = [mock_sent]
    mock_nlp.return_value = mock_doc

    return mock_nlp


@pytest.fixture
def mock_gazetteer():
    """Create a mock Gazetteer."""
    mock_gazetteer = MagicMock()
    return mock_gazetteer


def test_sentence_transformer_resolver_initialization_default():
    """Test SentenceTransformerResolver initialization with default parameters."""
    with patch(
        "geoparser.modules.resolvers.sentencetransformer.SentenceTransformer"
    ) as mock_st:
        with patch(
            "geoparser.modules.resolvers.sentencetransformer.AutoTokenizer"
        ) as mock_tokenizer:
            with patch(
                "geoparser.modules.resolvers.sentencetransformer.spacy"
            ) as mock_spacy:
                with patch(
                    "geoparser.modules.resolvers.sentencetransformer.Gazetteer"
                ) as mock_gaz:
                    with patch.object(
                        SentenceTransformerResolver, "_load", return_value="mock-id"
                    ):
                        resolver = SentenceTransformerResolver()

                        assert resolver.name == "SentenceTransformerResolver"
                        assert resolver.model_name == "dguzh/geo-all-MiniLM-L6-v2"
                        assert resolver.gazetteer_name == "geonames"
                        assert resolver.min_similarity == 0.7
                        assert resolver.max_iter == 3

                        # Verify components were initialized
                        mock_st.assert_called_once_with("dguzh/geo-all-MiniLM-L6-v2")
                        mock_tokenizer.from_pretrained.assert_called_once()
                        mock_spacy.load.assert_called_once_with("xx_sent_ud_sm")
                        mock_gaz.assert_called_once_with("geonames")


def test_sentence_transformer_resolver_initialization_custom():
    """Test SentenceTransformerResolver initialization with custom parameters."""
    with patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer"):
        with patch("geoparser.modules.resolvers.sentencetransformer.AutoTokenizer"):
            with patch("geoparser.modules.resolvers.sentencetransformer.spacy"):
                with patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer"):
                    with patch.object(
                        SentenceTransformerResolver, "_load", return_value="mock-id"
                    ):
                        resolver = SentenceTransformerResolver(
                            model_name="custom-model",
                            gazetteer_name="swissnames3d",
                            min_similarity=0.8,
                            max_iter=5,
                        )

                        assert resolver.model_name == "custom-model"
                        assert resolver.gazetteer_name == "swissnames3d"
                        assert resolver.min_similarity == 0.8
                        assert resolver.max_iter == 5


def test_predict_referents_empty_references():
    """Test predict_referents with empty reference list."""
    with patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer"):
        with patch("geoparser.modules.resolvers.sentencetransformer.AutoTokenizer"):
            with patch("geoparser.modules.resolvers.sentencetransformer.spacy"):
                with patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer"):
                    with patch.object(
                        SentenceTransformerResolver, "_load", return_value="mock-id"
                    ):
                        resolver = SentenceTransformerResolver()
                        result = resolver.predict_referents([])
                        assert result == []


def test_extract_contexts_single_reference(
    mock_references, mock_sentence_transformer, mock_tokenizer, mock_spacy_nlp
):
    """Test _extract_contexts with a single reference."""
    with patch(
        "geoparser.modules.resolvers.sentencetransformer.SentenceTransformer",
        return_value=mock_sentence_transformer,
    ):
        with patch(
            "geoparser.modules.resolvers.sentencetransformer.AutoTokenizer.from_pretrained",
            return_value=mock_tokenizer,
        ):
            with patch(
                "geoparser.modules.resolvers.sentencetransformer.spacy.load",
                return_value=mock_spacy_nlp,
            ):
                with patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer"):
                    with patch.object(
                        SentenceTransformerResolver, "_load", return_value="mock-id"
                    ):
                        resolver = SentenceTransformerResolver()

                        # Mock that document fits within token limit
                        mock_tokenizer.tokenize.return_value = [
                            "I",
                            "visited",
                            "London",
                            "last",
                            "summer",
                            ".",
                        ]

                        contexts = resolver._extract_contexts([mock_references[0]])

                        assert len(contexts) == 1
                        assert contexts[0] == "I visited London last summer."


def test_extract_contexts_long_document(
    mock_references, mock_sentence_transformer, mock_tokenizer, mock_spacy_nlp
):
    """Test _extract_contexts with a document that exceeds token limit."""
    with patch(
        "geoparser.modules.resolvers.sentencetransformer.SentenceTransformer",
        return_value=mock_sentence_transformer,
    ):
        with patch(
            "geoparser.modules.resolvers.sentencetransformer.AutoTokenizer.from_pretrained",
            return_value=mock_tokenizer,
        ):
            with patch(
                "geoparser.modules.resolvers.sentencetransformer.spacy.load",
                return_value=mock_spacy_nlp,
            ):
                with patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer"):
                    with patch.object(
                        SentenceTransformerResolver, "_load", return_value="mock-id"
                    ):
                        resolver = SentenceTransformerResolver()

                        # Mock that document exceeds token limit (first call returns too many tokens)
                        def mock_tokenize(text):
                            if text == mock_references[0].document.text:
                                return ["token"] * 600  # Exceeds limit of 510 (512-2)
                            else:
                                return [
                                    "I",
                                    "visited",
                                    "London",
                                    "last",
                                    "summer",
                                    ".",
                                ]  # Sentence tokens

                        mock_tokenizer.tokenize.side_effect = mock_tokenize

                        contexts = resolver._extract_contexts([mock_references[0]])

                        assert len(contexts) == 1
                        # Should return the sentence context
                        assert contexts[0] == "I visited London last summer."


def test_generate_description_geonames(mock_features):
    """Test _generate_description with GeoNames feature."""
    with patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer"):
        with patch("geoparser.modules.resolvers.sentencetransformer.AutoTokenizer"):
            with patch("geoparser.modules.resolvers.sentencetransformer.spacy"):
                with patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer"):
                    with patch.object(
                        SentenceTransformerResolver, "_load", return_value="mock-id"
                    ):
                        resolver = SentenceTransformerResolver(
                            gazetteer_name="geonames"
                        )

                        description = resolver._generate_description(mock_features[0])

                        expected = "London (populated place) in England, United Kingdom"
                        assert description == expected


def test_generate_description_swissnames3d():
    """Test _generate_description with SwissNames3D feature."""
    mock_feature = MagicMock()
    mock_feature.data = {
        "NAME": "Zurich",
        "OBJEKTART": "Stadt",
        "KANTON_NAME": "Zürich",
        "GEMEINDE_NAME": "Zürich",
    }

    with patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer"):
        with patch("geoparser.modules.resolvers.sentencetransformer.AutoTokenizer"):
            with patch("geoparser.modules.resolvers.sentencetransformer.spacy"):
                with patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer"):
                    with patch.object(
                        SentenceTransformerResolver, "_load", return_value="mock-id"
                    ):
                        resolver = SentenceTransformerResolver(
                            gazetteer_name="swissnames3d"
                        )

                        description = resolver._generate_description(mock_feature)

                        expected = "Zurich (Stadt) in Zürich, Zürich"
                        assert description == expected


def test_generate_description_unsupported_gazetteer():
    """Test _generate_description with unsupported gazetteer."""
    mock_feature = MagicMock()
    mock_feature.data = {"name": "Test"}

    with patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer"):
        with patch("geoparser.modules.resolvers.sentencetransformer.AutoTokenizer"):
            with patch("geoparser.modules.resolvers.sentencetransformer.spacy"):
                with patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer"):
                    with patch.object(
                        SentenceTransformerResolver, "_load", return_value="mock-id"
                    ):
                        resolver = SentenceTransformerResolver(
                            gazetteer_name="unsupported"
                        )

                        with pytest.raises(
                            ValueError,
                            match="Gazetteer 'unsupported' is not configured",
                        ):
                            resolver._generate_description(mock_feature)


def test_calculate_similarities():
    """Test _calculate_similarities method."""
    with patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer"):
        with patch("geoparser.modules.resolvers.sentencetransformer.AutoTokenizer"):
            with patch("geoparser.modules.resolvers.sentencetransformer.spacy"):
                with patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer"):
                    with patch.object(
                        SentenceTransformerResolver, "_load", return_value="mock-id"
                    ):
                        resolver = SentenceTransformerResolver()

                        # Create mock embeddings
                        reference_embedding = torch.tensor([1.0, 0.0, 0.0])
                        candidate_embeddings = [
                            torch.tensor([1.0, 0.0, 0.0]),  # Perfect match
                            torch.tensor([0.0, 1.0, 0.0]),  # Orthogonal
                            torch.tensor([0.5, 0.5, 0.0]),  # Partial match
                        ]

                        similarities = resolver._calculate_similarities(
                            reference_embedding, candidate_embeddings
                        )

                        assert len(similarities) == 3
                        # Perfect match should have similarity ~1.0
                        assert similarities[0] == pytest.approx(1.0, abs=1e-6)
                        # Orthogonal should have similarity ~0.0
                        assert similarities[1] == pytest.approx(0.0, abs=1e-6)
                        # Partial match should be somewhere in between
                        assert 0.0 < similarities[2] < 1.0


def test_calculate_similarities_empty_candidates():
    """Test _calculate_similarities with empty candidate list."""
    with patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer"):
        with patch("geoparser.modules.resolvers.sentencetransformer.AutoTokenizer"):
            with patch("geoparser.modules.resolvers.sentencetransformer.spacy"):
                with patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer"):
                    with patch.object(
                        SentenceTransformerResolver, "_load", return_value="mock-id"
                    ):
                        resolver = SentenceTransformerResolver()

                        reference_embedding = torch.tensor([1.0, 0.0, 0.0])
                        similarities = resolver._calculate_similarities(
                            reference_embedding, []
                        )

                        assert similarities == []


def test_embed_references_caching(mock_references):
    """Test that _embed_references avoids duplicate work through caching."""
    mock_transformer = MagicMock()
    mock_transformer.encode.return_value = torch.randn(1, 384)  # Single embedding

    with patch(
        "geoparser.modules.resolvers.sentencetransformer.SentenceTransformer",
        return_value=mock_transformer,
    ):
        with patch("geoparser.modules.resolvers.sentencetransformer.AutoTokenizer"):
            with patch("geoparser.modules.resolvers.sentencetransformer.spacy"):
                with patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer"):
                    with patch.object(
                        SentenceTransformerResolver, "_load", return_value="mock-id"
                    ):
                        resolver = SentenceTransformerResolver()

                        # Mock _extract_contexts to return identical contexts
                        with patch.object(
                            resolver,
                            "_extract_contexts",
                            return_value=["same context", "same context"],
                        ):
                            resolver._embed_references(mock_references)

                            # Should only encode once due to identical contexts
                            mock_transformer.encode.assert_called_once_with(
                                ["same context"],
                                convert_to_tensor=True,
                                batch_size=32,
                                show_progress_bar=True,
                            )

                            # Both references should have embeddings stored
                            assert 1 in resolver.reference_embeddings
                            assert 2 in resolver.reference_embeddings


def test_sentence_transformer_resolver_config():
    """Test that SentenceTransformerResolver correctly stores configuration."""
    with patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer"):
        with patch("geoparser.modules.resolvers.sentencetransformer.AutoTokenizer"):
            with patch("geoparser.modules.resolvers.sentencetransformer.spacy"):
                with patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer"):
                    with patch.object(
                        SentenceTransformerResolver, "_load", return_value="mock-id"
                    ):
                        resolver = SentenceTransformerResolver(
                            model_name="custom-model",
                            gazetteer_name="swissnames3d",
                            min_similarity=0.8,
                            max_iter=5,
                        )

                        expected_config = {
                            "gazetteer_name": "swissnames3d",
                            "max_iter": 5,
                            "min_similarity": 0.8,
                            "model_name": "custom-model",
                        }
                        assert resolver.config == expected_config


def test_predict_referents_integration(mock_references, mock_features):
    """Test predict_referents integration with mocked components."""
    mock_transformer = MagicMock()
    mock_transformer.encode.return_value = torch.randn(2, 384)
    mock_transformer.get_max_seq_length.return_value = 512

    mock_tokenizer = MagicMock()
    mock_tokenizer.tokenize.return_value = ["few", "tokens"]

    mock_gazetteer = MagicMock()
    mock_gazetteer.search.return_value = mock_features[:1]  # Return first feature

    with patch(
        "geoparser.modules.resolvers.sentencetransformer.SentenceTransformer",
        return_value=mock_transformer,
    ):
        with patch(
            "geoparser.modules.resolvers.sentencetransformer.AutoTokenizer.from_pretrained",
            return_value=mock_tokenizer,
        ):
            with patch("geoparser.modules.resolvers.sentencetransformer.spacy.load"):
                with patch(
                    "geoparser.modules.resolvers.sentencetransformer.Gazetteer",
                    return_value=mock_gazetteer,
                ):
                    with patch.object(
                        SentenceTransformerResolver, "_load", return_value="mock-id"
                    ):
                        resolver = SentenceTransformerResolver()

                        # Mock calculate_similarities to return high similarity
                        with patch.object(
                            resolver, "_calculate_similarities", return_value=[0.9]
                        ):
                            result = resolver.predict_referents(mock_references[:1])

                            assert len(result) == 1
                            assert result[0] == ("geonames", "2643743")
