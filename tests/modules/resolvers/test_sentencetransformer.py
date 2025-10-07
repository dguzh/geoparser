import tempfile
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
                        result = resolver.predict_referents([], [])
                        assert result == []


def test_extract_context_single_reference(
    mock_references, mock_sentence_transformer, mock_tokenizer, mock_spacy_nlp
):
    """Test _extract_context with a single reference."""
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

                        # Use raw data instead of Reference object
                        text = "I visited London last summer."
                        start = 10
                        end = 16
                        context = resolver._extract_context(text, start, end)

                        assert context == "I visited London last summer."


def test_extract_context_long_document(
    mock_references, mock_sentence_transformer, mock_tokenizer, mock_spacy_nlp
):
    """Test _extract_context with a document that exceeds token limit."""
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
                        text = "I visited London last summer."

                        def mock_tokenize(t):
                            if t == text:
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

                        # Use raw data instead of Reference object
                        start = 10
                        end = 16
                        context = resolver._extract_context(text, start, end)

                        # Should return the sentence context
                        assert context == "I visited London last summer."


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


def test_embed_contexts_caching():
    """Test that _embed_contexts avoids duplicate work through caching."""
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

                        # Test with identical contexts (should only encode once)
                        contexts = [["same context", "same context"]]
                        resolver._embed_contexts(contexts)

                        # Should only encode once due to identical contexts
                        mock_transformer.encode.assert_called_once_with(
                            ["same context"],
                            convert_to_tensor=True,
                            batch_size=32,
                            show_progress_bar=True,
                        )

                        # Context should have embedding stored
                        assert "same context" in resolver.context_embeddings


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
                            # Use raw data instead of Reference objects
                            texts = ["I visited London last summer."]
                            references = [[(10, 16)]]  # "London"
                            result = resolver.predict_referents(texts, references)

                            assert len(result) == 1
                            assert len(result[0]) == 1
                            assert result[0][0] == ("geonames", "2643743")


def test_prepare_training_data_empty_documents():
    """Test _prepare_training_data with empty document list."""
    with patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer"):
        with patch("geoparser.modules.resolvers.sentencetransformer.AutoTokenizer"):
            with patch("geoparser.modules.resolvers.sentencetransformer.spacy"):
                with patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer"):
                    with patch.object(
                        SentenceTransformerResolver, "_load", return_value="mock-id"
                    ):
                        resolver = SentenceTransformerResolver()

                        result = resolver._prepare_training_data([], [], [])

                        assert result == {"sentence1": [], "sentence2": [], "label": []}


def test_prepare_training_data_no_referents():
    """Test _prepare_training_data with documents that have no resolved references."""
    texts = ["Some text"]
    references = [[]]  # No references
    referents = [[]]

    with patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer"):
        with patch("geoparser.modules.resolvers.sentencetransformer.AutoTokenizer"):
            with patch("geoparser.modules.resolvers.sentencetransformer.spacy"):
                with patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer"):
                    with patch.object(
                        SentenceTransformerResolver, "_load", return_value="mock-id"
                    ):
                        resolver = SentenceTransformerResolver()

                        result = resolver._prepare_training_data(
                            texts, references, referents
                        )

                        assert result == {"sentence1": [], "sentence2": [], "label": []}


def test_prepare_training_data_with_referents():
    """Test _prepare_training_data with documents containing resolved references."""
    texts = ["I visited London"]
    references = [[(10, 16)]]  # "London"
    referents = [[("geonames", "2643743")]]

    # Create mock candidates
    mock_candidate1 = MagicMock()
    mock_candidate1.identifier_value = "2643743"  # Correct candidate
    mock_candidate2 = MagicMock()
    mock_candidate2.identifier_value = "5128581"  # Incorrect candidate

    mock_gazetteer = MagicMock()
    mock_gazetteer.search.return_value = [mock_candidate1, mock_candidate2]

    with patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer"):
        with patch("geoparser.modules.resolvers.sentencetransformer.AutoTokenizer"):
            with patch("geoparser.modules.resolvers.sentencetransformer.spacy"):
                with patch(
                    "geoparser.modules.resolvers.sentencetransformer.Gazetteer",
                    return_value=mock_gazetteer,
                ):
                    with patch.object(
                        SentenceTransformerResolver, "_load", return_value="mock-id"
                    ):
                        resolver = SentenceTransformerResolver()

                        # Mock the context extraction and description generation
                        with patch.object(
                            resolver, "_extract_context", return_value="test context"
                        ):
                            with patch.object(
                                resolver,
                                "_generate_description",
                                side_effect=["desc1", "desc2"],
                            ):
                                result = resolver._prepare_training_data(
                                    texts, references, referents
                                )

                                # Should have 2 training examples (positive and negative)
                                assert len(result["sentence1"]) == 2
                                assert len(result["sentence2"]) == 2
                                assert len(result["label"]) == 2

                                # Check contexts are correct
                                assert all(
                                    ctx == "test context" for ctx in result["sentence1"]
                                )

                                # Check descriptions
                                assert result["sentence2"] == ["desc1", "desc2"]

                                # Check labels (first should be positive, second negative)
                                assert result["label"] == [1, 0]


def test_fit_empty_documents():
    """Test fit method with empty document list."""
    with patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer"):
        with patch("geoparser.modules.resolvers.sentencetransformer.AutoTokenizer"):
            with patch("geoparser.modules.resolvers.sentencetransformer.spacy"):
                with patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer"):
                    with patch.object(
                        SentenceTransformerResolver, "_load", return_value="mock-id"
                    ):
                        resolver = SentenceTransformerResolver()

                        with tempfile.TemporaryDirectory() as temp_dir:
                            with pytest.raises(
                                ValueError, match="No training examples found"
                            ):
                                resolver.fit([], [], [], temp_dir)


def test_fit_no_training_examples():
    """Test fit method with documents that produce no training examples."""
    texts = ["Some text"]
    references = [[]]  # No references
    referents = [[]]

    with patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer"):
        with patch("geoparser.modules.resolvers.sentencetransformer.AutoTokenizer"):
            with patch("geoparser.modules.resolvers.sentencetransformer.spacy"):
                with patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer"):
                    with patch.object(
                        SentenceTransformerResolver, "_load", return_value="mock-id"
                    ):
                        resolver = SentenceTransformerResolver()

                        with tempfile.TemporaryDirectory() as temp_dir:
                            with pytest.raises(
                                ValueError, match="No training examples found"
                            ):
                                resolver.fit(texts, references, referents, temp_dir)


def test_fit_successful_training():
    """Test fit method with successful training."""
    # Mock training data preparation
    training_data = {
        "sentence1": ["context1", "context2"],
        "sentence2": ["desc1", "desc2"],
        "label": [1, 0],
    }

    texts = ["Some text"]
    references = [[(0, 4)]]
    referents = [[("geonames", "123")]]

    mock_transformer = MagicMock()
    mock_trainer = MagicMock()

    with patch(
        "geoparser.modules.resolvers.sentencetransformer.SentenceTransformer",
        return_value=mock_transformer,
    ):
        with patch("geoparser.modules.resolvers.sentencetransformer.AutoTokenizer"):
            with patch("geoparser.modules.resolvers.sentencetransformer.spacy"):
                with patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer"):
                    with patch(
                        "geoparser.modules.resolvers.sentencetransformer.SentenceTransformerTrainer",
                        return_value=mock_trainer,
                    ):
                        with patch(
                            "geoparser.modules.resolvers.sentencetransformer.ContrastiveLoss"
                        ) as mock_loss:
                            with patch(
                                "geoparser.modules.resolvers.sentencetransformer.SentenceTransformerTrainingArguments"
                            ) as mock_args:
                                with patch(
                                    "geoparser.modules.resolvers.sentencetransformer.Dataset.from_dict"
                                ) as mock_dataset:
                                    with patch.object(
                                        SentenceTransformerResolver,
                                        "_load",
                                        return_value="mock-id",
                                    ):
                                        resolver = SentenceTransformerResolver()

                                        # Mock _prepare_training_data to return test data
                                        with patch.object(
                                            resolver,
                                            "_prepare_training_data",
                                            return_value=training_data,
                                        ):
                                            with tempfile.TemporaryDirectory() as temp_dir:
                                                resolver.fit(
                                                    texts,
                                                    references,
                                                    referents,
                                                    temp_dir,
                                                    epochs=2,
                                                    batch_size=4,
                                                )

                                                # Verify training was called
                                                mock_trainer.train.assert_called_once()

                                                # Verify model was saved
                                                mock_transformer.save_pretrained.assert_called_once_with(
                                                    temp_dir
                                                )

                                                # Verify dataset was created with correct data
                                                mock_dataset.assert_called_once_with(
                                                    training_data
                                                )

                                                # Verify training arguments were set correctly
                                                mock_args.assert_called_once()
                                                args_call = mock_args.call_args[1]
                                                assert (
                                                    args_call["output_dir"] == temp_dir
                                                )
                                                assert (
                                                    args_call["num_train_epochs"] == 2
                                                )
                                                assert (
                                                    args_call[
                                                        "per_device_train_batch_size"
                                                    ]
                                                    == 4
                                                )


def test_fit_custom_parameters():
    """Test fit method with custom training parameters."""
    training_data = {"sentence1": ["context1"], "sentence2": ["desc1"], "label": [1]}

    texts = ["Some text"]
    references = [[(0, 4)]]
    referents = [[("geonames", "123")]]

    mock_transformer = MagicMock()
    mock_trainer = MagicMock()

    with patch(
        "geoparser.modules.resolvers.sentencetransformer.SentenceTransformer",
        return_value=mock_transformer,
    ):
        with patch("geoparser.modules.resolvers.sentencetransformer.AutoTokenizer"):
            with patch("geoparser.modules.resolvers.sentencetransformer.spacy"):
                with patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer"):
                    with patch(
                        "geoparser.modules.resolvers.sentencetransformer.SentenceTransformerTrainer",
                        return_value=mock_trainer,
                    ):
                        with patch(
                            "geoparser.modules.resolvers.sentencetransformer.ContrastiveLoss"
                        ):
                            with patch(
                                "geoparser.modules.resolvers.sentencetransformer.SentenceTransformerTrainingArguments"
                            ) as mock_args:
                                with patch(
                                    "geoparser.modules.resolvers.sentencetransformer.Dataset.from_dict"
                                ):
                                    with patch.object(
                                        SentenceTransformerResolver,
                                        "_load",
                                        return_value="mock-id",
                                    ):
                                        resolver = SentenceTransformerResolver()

                                        with patch.object(
                                            resolver,
                                            "_prepare_training_data",
                                            return_value=training_data,
                                        ):
                                            with tempfile.TemporaryDirectory() as temp_dir:
                                                resolver.fit(
                                                    texts,
                                                    references,
                                                    referents,
                                                    temp_dir,
                                                    epochs=5,
                                                    batch_size=16,
                                                    learning_rate=1e-4,
                                                    warmup_ratio=0.2,
                                                    save_strategy="steps",
                                                )

                                                # Verify custom parameters were passed
                                                args_call = mock_args.call_args[1]
                                                assert (
                                                    args_call["num_train_epochs"] == 5
                                                )
                                                assert (
                                                    args_call[
                                                        "per_device_train_batch_size"
                                                    ]
                                                    == 16
                                                )
                                                assert (
                                                    args_call["learning_rate"] == 1e-4
                                                )
                                                assert args_call["warmup_ratio"] == 0.2
                                                assert (
                                                    args_call["save_strategy"]
                                                    == "steps"
                                                )


def test_predict_referents_exact_method_skip_on_higher_ranks():
    """Test that exact method is skipped for ranks > 1."""
    mock_references = [MagicMock()]
    mock_references[0].id = 1
    mock_references[0].text = "London"

    mock_transformer = MagicMock()
    mock_transformer.encode.return_value = torch.randn(1, 384)
    mock_transformer.get_max_seq_length.return_value = 512

    mock_gazetteer = MagicMock()
    mock_gazetteer.search.return_value = []  # No candidates found

    with patch(
        "geoparser.modules.resolvers.sentencetransformer.SentenceTransformer",
        return_value=mock_transformer,
    ):
        with patch("geoparser.modules.resolvers.sentencetransformer.AutoTokenizer"):
            with patch("geoparser.modules.resolvers.sentencetransformer.spacy"):
                with patch(
                    "geoparser.modules.resolvers.sentencetransformer.Gazetteer",
                    return_value=mock_gazetteer,
                ):
                    with patch.object(
                        SentenceTransformerResolver, "_load", return_value="mock-id"
                    ):
                        resolver = SentenceTransformerResolver(max_iter=2)

                        # Mock _extract_context to return a simple context
                        with patch.object(
                            resolver, "_extract_context", return_value="test context"
                        ):
                            # Use raw data
                            texts = ["I visited London"]
                            references = [[(10, 16)]]  # "London"
                            result = resolver.predict_referents(texts, references)

                            # Should return default result since no candidates found
                            assert result == [[("geonames", "")]]

                            # Verify exact method was called only for ranks=1
                            search_calls = mock_gazetteer.search.call_args_list
                            exact_calls = [
                                call
                                for call in search_calls
                                if len(call[0]) > 1 and call[0][1] == "exact"
                            ]
                            # Should only have 1 exact call (for ranks=1)
                            assert len(exact_calls) == 1


def test_embed_contexts_empty_list():
    """Test _embed_contexts with empty contexts list."""
    with patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer"):
        with patch("geoparser.modules.resolvers.sentencetransformer.AutoTokenizer"):
            with patch("geoparser.modules.resolvers.sentencetransformer.spacy"):
                with patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer"):
                    with patch.object(
                        SentenceTransformerResolver, "_load", return_value="mock-id"
                    ):
                        resolver = SentenceTransformerResolver()

                        # Call with empty list should return early
                        resolver._embed_contexts([])

                        # Verify no embeddings were stored
                        assert len(resolver.context_embeddings) == 0


def test_gather_candidates_already_resolved():
    """Test _gather_candidates skips already resolved references."""
    mock_reference = MagicMock()
    mock_reference.text = "London"

    mock_gazetteer = MagicMock()

    with patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer"):
        with patch("geoparser.modules.resolvers.sentencetransformer.AutoTokenizer"):
            with patch("geoparser.modules.resolvers.sentencetransformer.spacy"):
                with patch(
                    "geoparser.modules.resolvers.sentencetransformer.Gazetteer",
                    return_value=mock_gazetteer,
                ):
                    with patch.object(
                        SentenceTransformerResolver, "_load", return_value="mock-id"
                    ):
                        resolver = SentenceTransformerResolver()

                        # Use new nested structure
                        texts = ["I visited London"]
                        references = [[(10, 16)]]  # "London"
                        candidates = [[[]]]  # No candidates yet
                        results = [[("geonames", "123")]]  # Already resolved

                        resolver._gather_candidates(
                            texts, references, candidates, results, "exact", 1
                        )

                        # Should not have called search since reference is already resolved
                        mock_gazetteer.search.assert_not_called()


def test_embed_candidates_already_resolved():
    """Test _embed_candidates skips already resolved references."""
    mock_candidate = MagicMock()
    mock_candidate.id = 1

    with patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer"):
        with patch("geoparser.modules.resolvers.sentencetransformer.AutoTokenizer"):
            with patch("geoparser.modules.resolvers.sentencetransformer.spacy"):
                with patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer"):
                    with patch.object(
                        SentenceTransformerResolver, "_load", return_value="mock-id"
                    ):
                        resolver = SentenceTransformerResolver()

                        candidates = [[mock_candidate]]
                        results = [("geonames", "123")]  # Already resolved

                        resolver._embed_candidates(candidates, results)

                        # Should not have stored any embeddings since reference is resolved
                        assert len(resolver.candidate_embeddings) == 0


def test_embed_candidates_no_candidates_to_embed():
    """Test _embed_candidates when all candidates already have embeddings."""
    mock_candidate = MagicMock()
    mock_candidate.id = 1

    mock_transformer = MagicMock()

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

                        # Pre-populate candidate embeddings
                        resolver.candidate_embeddings[1] = torch.randn(384)

                        candidates = [
                            [[mock_candidate]]
                        ]  # Nested: doc -> ref -> candidates
                        results = [[None]]  # Not resolved yet

                        resolver._embed_candidates(candidates, results)

                        # Should not have called encode since candidate already has embedding
                        mock_transformer.encode.assert_not_called()


def test_evaluate_candidates_no_candidates():
    """Test _evaluate_candidates when reference has no candidates."""
    mock_reference = MagicMock()
    mock_reference.id = 1

    with patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer"):
        with patch("geoparser.modules.resolvers.sentencetransformer.AutoTokenizer"):
            with patch("geoparser.modules.resolvers.sentencetransformer.spacy"):
                with patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer"):
                    with patch.object(
                        SentenceTransformerResolver, "_load", return_value="mock-id"
                    ):
                        resolver = SentenceTransformerResolver()

                        # Add context embedding
                        resolver.context_embeddings["test context"] = torch.randn(384)

                        contexts = [["test context"]]  # One document with one reference
                        candidates = [[[]]]  # No candidates for that reference
                        results = [[None]]  # Not resolved yet

                        resolver._evaluate_candidates(contexts, candidates, results)

                        # Result should remain None since no candidates to evaluate
                        assert results[0][0] is None


def test_extract_context_with_previous_sentence_expansion():
    """Test _extract_context when expanding context to include previous sentences."""
    mock_reference = MagicMock()
    mock_reference.start = 50
    mock_reference.end = 56
    mock_reference.document.text = (
        "Previous sentence here. Target sentence with London here. Next sentence here."
    )

    mock_transformer = MagicMock()
    mock_transformer.get_max_seq_length.return_value = 512

    mock_tokenizer = MagicMock()

    def mock_tokenize(text):
        # Make document exceed token limit, but individual sentences fit
        if (
            "Previous sentence here. Target sentence with London here. Next sentence here."
            in text
        ):
            return ["token"] * 600  # Exceeds limit
        elif "Previous sentence here." in text:
            return ["prev"] * 5
        elif "Target sentence with London here." in text:
            return ["target"] * 5
        elif "Next sentence here." in text:
            return ["next"] * 5
        else:
            return ["token"] * 5

    mock_tokenizer.tokenize.side_effect = mock_tokenize

    # Create mock sentences
    mock_prev_sent = MagicMock()
    mock_prev_sent.start_char = 0
    mock_prev_sent.end_char = 23
    mock_prev_sent.text = "Previous sentence here."

    mock_target_sent = MagicMock()
    mock_target_sent.start_char = 24
    mock_target_sent.end_char = 56
    mock_target_sent.text = "Target sentence with London here."

    mock_next_sent = MagicMock()
    mock_next_sent.start_char = 57
    mock_next_sent.end_char = 76
    mock_next_sent.text = "Next sentence here."

    mock_nlp = MagicMock()
    mock_doc = MagicMock()
    mock_doc.sents = [mock_prev_sent, mock_target_sent, mock_next_sent]
    mock_nlp.return_value = mock_doc

    with patch(
        "geoparser.modules.resolvers.sentencetransformer.SentenceTransformer",
        return_value=mock_transformer,
    ):
        with patch(
            "geoparser.modules.resolvers.sentencetransformer.AutoTokenizer.from_pretrained",
            return_value=mock_tokenizer,
        ):
            with patch(
                "geoparser.modules.resolvers.sentencetransformer.spacy.load",
                return_value=mock_nlp,
            ):
                with patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer"):
                    with patch.object(
                        SentenceTransformerResolver, "_load", return_value="mock-id"
                    ):
                        resolver = SentenceTransformerResolver()

                        # Use raw data instead of Reference object
                        text = mock_reference.document.text
                        start = mock_reference.start
                        end = mock_reference.end
                        context = resolver._extract_context(text, start, end)

                        # Should include previous and target sentences (and next if it fits)
                        expected = "Previous sentence here. Target sentence with London here. Next sentence here."
                        assert context == expected


def test_extract_context_with_next_sentence_expansion():
    """Test _extract_context when expanding context to include next sentences."""
    mock_reference = MagicMock()
    mock_reference.start = 24
    mock_reference.end = 30
    mock_reference.document.text = (
        "Target sentence with London here. Next sentence here."
    )

    mock_transformer = MagicMock()
    mock_transformer.get_max_seq_length.return_value = 512

    mock_tokenizer = MagicMock()

    def mock_tokenize(text):
        # Make document exceed token limit, but individual sentences fit
        if "Target sentence with London here. Next sentence here." in text:
            return ["token"] * 600  # Exceeds limit
        elif "Target sentence with London here." in text:
            return ["target"] * 5
        elif "Next sentence here." in text:
            return ["next"] * 5
        else:
            return ["token"] * 5

    mock_tokenizer.tokenize.side_effect = mock_tokenize

    # Create mock sentences - only target and next (no previous)
    mock_target_sent = MagicMock()
    mock_target_sent.start_char = 0
    mock_target_sent.end_char = 32
    mock_target_sent.text = "Target sentence with London here."

    mock_next_sent = MagicMock()
    mock_next_sent.start_char = 33
    mock_next_sent.end_char = 52
    mock_next_sent.text = "Next sentence here."

    mock_nlp = MagicMock()
    mock_doc = MagicMock()
    mock_doc.sents = [mock_target_sent, mock_next_sent]
    mock_nlp.return_value = mock_doc

    with patch(
        "geoparser.modules.resolvers.sentencetransformer.SentenceTransformer",
        return_value=mock_transformer,
    ):
        with patch(
            "geoparser.modules.resolvers.sentencetransformer.AutoTokenizer.from_pretrained",
            return_value=mock_tokenizer,
        ):
            with patch(
                "geoparser.modules.resolvers.sentencetransformer.spacy.load",
                return_value=mock_nlp,
            ):
                with patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer"):
                    with patch.object(
                        SentenceTransformerResolver, "_load", return_value="mock-id"
                    ):
                        resolver = SentenceTransformerResolver()

                        # Use raw data instead of Reference object
                        text = mock_reference.document.text
                        start = mock_reference.start
                        end = mock_reference.end
                        context = resolver._extract_context(text, start, end)

                        # Should include both target and next sentences
                        expected = (
                            "Target sentence with London here. Next sentence here."
                        )
                        assert context == expected
