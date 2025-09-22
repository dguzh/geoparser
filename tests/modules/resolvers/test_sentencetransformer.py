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
                        result = resolver.predict_referents([])
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

                        context = resolver._extract_context(mock_references[0])

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

                        context = resolver._extract_context(mock_references[0])

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

                        # Mock _extract_context to return identical contexts
                        with patch.object(
                            resolver,
                            "_extract_context",
                            return_value="same context",
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

                        result = resolver._prepare_training_data([])

                        assert result == {"sentence1": [], "sentence2": [], "label": []}


def test_prepare_training_data_no_referents():
    """Test _prepare_training_data with documents that have no resolved references."""
    mock_document = MagicMock()
    mock_reference = MagicMock()
    mock_reference.referents = []  # No resolved referents
    mock_document.references = [mock_reference]

    with patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer"):
        with patch("geoparser.modules.resolvers.sentencetransformer.AutoTokenizer"):
            with patch("geoparser.modules.resolvers.sentencetransformer.spacy"):
                with patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer"):
                    with patch.object(
                        SentenceTransformerResolver, "_load", return_value="mock-id"
                    ):
                        resolver = SentenceTransformerResolver()

                        result = resolver._prepare_training_data([mock_document])

                        assert result == {"sentence1": [], "sentence2": [], "label": []}


def test_prepare_training_data_with_referents():
    """Test _prepare_training_data with documents containing resolved references."""
    # Create mock document with resolved reference
    mock_document = MagicMock()
    mock_reference = MagicMock()
    mock_reference.text = "London"
    mock_reference.referents = [MagicMock()]
    mock_reference.referents[0].feature.identifier_value = "2643743"
    mock_document.references = [mock_reference]

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
                                    [mock_document]
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
                                resolver.fit([], temp_dir)


def test_fit_no_training_examples():
    """Test fit method with documents that produce no training examples."""
    mock_document = MagicMock()
    mock_document.references = []  # No references

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
                                resolver.fit([mock_document], temp_dir)


def test_fit_successful_training():
    """Test fit method with successful training."""
    # Mock training data preparation
    training_data = {
        "sentence1": ["context1", "context2"],
        "sentence2": ["desc1", "desc2"],
        "label": [1, 0],
    }

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
                                                    [MagicMock()],
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
                                                    [MagicMock()],
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
