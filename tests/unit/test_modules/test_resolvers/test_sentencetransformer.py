"""
Unit tests for geoparser/modules/resolvers/sentencetransformer.py

Tests the SentenceTransformerResolver module with mocked dependencies.
"""

from unittest.mock import Mock, patch

import pytest
import torch


@pytest.mark.unit
class TestSentenceTransformerResolverInitialization:
    """Test SentenceTransformerResolver initialization."""

    @patch("geoparser.modules.resolvers.sentencetransformer.spacy.load")
    @patch(
        "geoparser.modules.resolvers.sentencetransformer.AutoTokenizer.from_pretrained"
    )
    @patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer")
    @patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer")
    def test_creates_with_default_parameters(
        self, mock_gazetteer, mock_transformer, mock_tokenizer, mock_spacy_load
    ):
        """Test that SentenceTransformerResolver can be created with default parameters."""
        # Arrange
        from geoparser.modules.resolvers.sentencetransformer import (
            SentenceTransformerResolver,
        )

        # Act
        resolver = SentenceTransformerResolver()

        # Assert
        assert resolver.name == "SentenceTransformerResolver"
        assert resolver.model_name == "dguzh/geo-all-MiniLM-L6-v2"
        assert resolver.gazetteer_name == "geonames"
        assert resolver.min_similarity == 0.7
        assert resolver.max_iter == 3

    @patch("geoparser.modules.resolvers.sentencetransformer.spacy.load")
    @patch(
        "geoparser.modules.resolvers.sentencetransformer.AutoTokenizer.from_pretrained"
    )
    @patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer")
    @patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer")
    def test_creates_with_custom_parameters(
        self, mock_gazetteer, mock_transformer, mock_tokenizer, mock_spacy_load
    ):
        """Test that SentenceTransformerResolver can be created with custom parameters."""
        # Arrange
        from geoparser.modules.resolvers.sentencetransformer import (
            SentenceTransformerResolver,
        )

        # Act
        resolver = SentenceTransformerResolver(
            model_name="custom-model",
            gazetteer_name="custom-gazetteer",
            min_similarity=0.8,
            max_iter=5,
        )

        # Assert
        assert resolver.model_name == "custom-model"
        assert resolver.gazetteer_name == "custom-gazetteer"
        assert resolver.min_similarity == 0.8
        assert resolver.max_iter == 5

    @patch("geoparser.modules.resolvers.sentencetransformer.spacy.load")
    @patch(
        "geoparser.modules.resolvers.sentencetransformer.AutoTokenizer.from_pretrained"
    )
    @patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer")
    @patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer")
    def test_config_contains_all_parameters(
        self, mock_gazetteer, mock_transformer, mock_tokenizer, mock_spacy_load
    ):
        """Test that config stores all initialization parameters."""
        # Arrange
        from geoparser.modules.resolvers.sentencetransformer import (
            SentenceTransformerResolver,
        )

        # Act
        resolver = SentenceTransformerResolver(
            model_name="test-model",
            gazetteer_name="test-gazetteer",
            min_similarity=0.75,
            max_iter=4,
        )

        # Assert
        assert resolver.config["model_name"] == "test-model"
        assert resolver.config["gazetteer_name"] == "test-gazetteer"
        assert resolver.config["min_similarity"] == 0.75
        assert resolver.config["max_iter"] == 4

    @patch("geoparser.modules.resolvers.sentencetransformer.spacy.load")
    @patch(
        "geoparser.modules.resolvers.sentencetransformer.AutoTokenizer.from_pretrained"
    )
    @patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer")
    @patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer")
    def test_loads_sentence_transformer_model(
        self, mock_gazetteer, mock_transformer_class, mock_tokenizer, mock_spacy_load
    ):
        """Test that SentenceTransformer model is loaded."""
        # Arrange
        from geoparser.modules.resolvers.sentencetransformer import (
            SentenceTransformerResolver,
        )

        # Act
        resolver = SentenceTransformerResolver(model_name="test-model")

        # Assert
        mock_transformer_class.assert_called_once_with("test-model")

    @patch("geoparser.modules.resolvers.sentencetransformer.spacy.load")
    @patch(
        "geoparser.modules.resolvers.sentencetransformer.AutoTokenizer.from_pretrained"
    )
    @patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer")
    @patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer")
    def test_loads_tokenizer(
        self, mock_gazetteer, mock_transformer, mock_tokenizer, mock_spacy_load
    ):
        """Test that AutoTokenizer is loaded."""
        # Arrange
        from geoparser.modules.resolvers.sentencetransformer import (
            SentenceTransformerResolver,
        )

        # Act
        resolver = SentenceTransformerResolver(model_name="test-model")

        # Assert
        mock_tokenizer.assert_called_once_with("test-model")

    @patch("geoparser.modules.resolvers.sentencetransformer.spacy.load")
    @patch(
        "geoparser.modules.resolvers.sentencetransformer.AutoTokenizer.from_pretrained"
    )
    @patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer")
    @patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer")
    def test_loads_spacy_sentence_splitter(
        self, mock_gazetteer, mock_transformer, mock_tokenizer, mock_spacy_load
    ):
        """Test that spaCy sentence splitter model is loaded."""
        # Arrange
        from geoparser.modules.resolvers.sentencetransformer import (
            SentenceTransformerResolver,
        )

        # Act
        resolver = SentenceTransformerResolver()

        # Assert
        mock_spacy_load.assert_called_once_with("xx_sent_ud_sm")

    @patch("geoparser.modules.resolvers.sentencetransformer.spacy.load")
    @patch(
        "geoparser.modules.resolvers.sentencetransformer.AutoTokenizer.from_pretrained"
    )
    @patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer")
    @patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer")
    def test_initializes_gazetteer(
        self, mock_gazetteer_class, mock_transformer, mock_tokenizer, mock_spacy_load
    ):
        """Test that Gazetteer is initialized."""
        # Arrange
        from geoparser.modules.resolvers.sentencetransformer import (
            SentenceTransformerResolver,
        )

        # Act
        resolver = SentenceTransformerResolver(gazetteer_name="test-gazetteer")

        # Assert
        mock_gazetteer_class.assert_called_once_with("test-gazetteer")

    @patch("geoparser.modules.resolvers.sentencetransformer.spacy.load")
    @patch(
        "geoparser.modules.resolvers.sentencetransformer.AutoTokenizer.from_pretrained"
    )
    @patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer")
    @patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer")
    def test_initializes_empty_caches(
        self, mock_gazetteer, mock_transformer, mock_tokenizer, mock_spacy_load
    ):
        """Test that embedding caches are initialized as empty dictionaries."""
        # Arrange
        from geoparser.modules.resolvers.sentencetransformer import (
            SentenceTransformerResolver,
        )

        # Act
        resolver = SentenceTransformerResolver()

        # Assert
        assert resolver.context_embeddings == {}
        assert resolver.candidate_embeddings == {}

    @patch("geoparser.modules.resolvers.sentencetransformer.spacy.load")
    @patch(
        "geoparser.modules.resolvers.sentencetransformer.AutoTokenizer.from_pretrained"
    )
    @patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer")
    @patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer")
    def test_different_configs_produce_different_ids(
        self, mock_gazetteer, mock_transformer, mock_tokenizer, mock_spacy_load
    ):
        """Test that different configurations produce different module IDs."""
        # Arrange
        from geoparser.modules.resolvers.sentencetransformer import (
            SentenceTransformerResolver,
        )

        # Act
        resolver1 = SentenceTransformerResolver(min_similarity=0.7)
        resolver2 = SentenceTransformerResolver(min_similarity=0.8)

        # Assert
        assert resolver1.id != resolver2.id

    @patch("geoparser.modules.resolvers.sentencetransformer.spacy.load")
    @patch(
        "geoparser.modules.resolvers.sentencetransformer.AutoTokenizer.from_pretrained"
    )
    @patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer")
    @patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer")
    def test_same_config_produces_same_id(
        self, mock_gazetteer, mock_transformer, mock_tokenizer, mock_spacy_load
    ):
        """Test that same configuration produces same module ID."""
        # Arrange
        from geoparser.modules.resolvers.sentencetransformer import (
            SentenceTransformerResolver,
        )

        # Act
        resolver1 = SentenceTransformerResolver(
            model_name="model1", gazetteer_name="gaz1", min_similarity=0.7, max_iter=3
        )
        resolver2 = SentenceTransformerResolver(
            model_name="model1", gazetteer_name="gaz1", min_similarity=0.7, max_iter=3
        )

        # Assert
        assert resolver1.id == resolver2.id


@pytest.mark.unit
class TestSentenceTransformerResolverPredict:
    """Test SentenceTransformerResolver predict method."""

    @patch("geoparser.modules.resolvers.sentencetransformer.spacy.load")
    @patch(
        "geoparser.modules.resolvers.sentencetransformer.AutoTokenizer.from_pretrained"
    )
    @patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer")
    @patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer")
    def test_handles_empty_text_list(
        self, mock_gazetteer, mock_transformer, mock_tokenizer, mock_spacy_load
    ):
        """Test that predict handles empty text list."""
        # Arrange
        from geoparser.modules.resolvers.sentencetransformer import (
            SentenceTransformerResolver,
        )

        resolver = SentenceTransformerResolver()

        # Act
        results = resolver.predict(texts=[], references=[])

        # Assert
        assert results == []

    @patch("geoparser.modules.resolvers.sentencetransformer.spacy.load")
    @patch(
        "geoparser.modules.resolvers.sentencetransformer.AutoTokenizer.from_pretrained"
    )
    @patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer")
    @patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer")
    def test_caches_context_embeddings(
        self, mock_gazetteer, mock_transformer, mock_tokenizer, mock_spacy_load
    ):
        """Test that context embeddings are cached to avoid recomputation."""
        # Arrange
        from geoparser.modules.resolvers.sentencetransformer import (
            SentenceTransformerResolver,
        )

        mock_transformer_instance = mock_transformer.return_value
        mock_transformer_instance.get_max_seq_length.return_value = 512
        mock_transformer_instance.encode.return_value = torch.tensor([[0.1, 0.2, 0.3]])

        mock_tokenizer_instance = mock_tokenizer.return_value
        mock_tokenizer_instance.tokenize.return_value = ["test"]

        # Mock gazetteer search
        mock_gazetteer_instance = mock_gazetteer.return_value
        mock_candidate = Mock()
        mock_candidate.id = 1
        mock_candidate.location_id_value = "123"
        mock_candidate.data = {
            "name": "Paris",
            "feature_name": "city",
            "country_name": "France",
        }
        mock_gazetteer_instance.search.return_value = [mock_candidate]

        resolver = SentenceTransformerResolver()

        # Act - Call predict twice with same text
        resolver.predict(texts=["Test"], references=[[(0, 4)]])
        call_count_first = mock_transformer_instance.encode.call_count

        resolver.predict(texts=["Test"], references=[[(0, 4)]])
        call_count_second = mock_transformer_instance.encode.call_count

        # Assert - encode should not be called again for the same context
        # (though it may be called for candidates)
        assert "Test" in resolver.context_embeddings

    @patch("geoparser.modules.resolvers.sentencetransformer.spacy.load")
    @patch(
        "geoparser.modules.resolvers.sentencetransformer.AutoTokenizer.from_pretrained"
    )
    @patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer")
    @patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer")
    def test_caches_candidate_embeddings(
        self, mock_gazetteer, mock_transformer, mock_tokenizer, mock_spacy_load
    ):
        """Test that candidate embeddings are cached to avoid recomputation."""
        # Arrange
        from geoparser.modules.resolvers.sentencetransformer import (
            SentenceTransformerResolver,
        )

        mock_transformer_instance = mock_transformer.return_value
        mock_transformer_instance.get_max_seq_length.return_value = 512
        mock_transformer_instance.encode.return_value = torch.tensor([[0.1, 0.2, 0.3]])

        mock_tokenizer_instance = mock_tokenizer.return_value
        mock_tokenizer_instance.tokenize.return_value = ["test"]

        # Mock gazetteer search
        mock_gazetteer_instance = mock_gazetteer.return_value
        mock_candidate = Mock()
        mock_candidate.id = 1
        mock_candidate.location_id_value = "123"
        mock_candidate.data = {
            "name": "Paris",
            "feature_name": "city",
            "country_name": "France",
        }
        mock_gazetteer_instance.search.return_value = [mock_candidate]

        resolver = SentenceTransformerResolver()

        # Act - Call predict twice
        resolver.predict(texts=["Test"], references=[[(0, 4)]])
        resolver.predict(texts=["Test"], references=[[(0, 4)]])

        # Assert - Candidate with id=1 should be in cache
        assert 1 in resolver.candidate_embeddings


@pytest.mark.unit
class TestSentenceTransformerResolverHelperMethods:
    """Test SentenceTransformerResolver helper methods."""

    @patch("geoparser.modules.resolvers.sentencetransformer.spacy.load")
    @patch(
        "geoparser.modules.resolvers.sentencetransformer.AutoTokenizer.from_pretrained"
    )
    @patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer")
    @patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer")
    def test_generate_description_geonames(
        self, mock_gazetteer, mock_transformer, mock_tokenizer, mock_spacy_load
    ):
        """Test that _generate_description creates proper descriptions for geonames."""
        # Arrange
        from geoparser.modules.resolvers.sentencetransformer import (
            SentenceTransformerResolver,
        )

        resolver = SentenceTransformerResolver(gazetteer_name="geonames")

        mock_candidate = Mock()
        mock_candidate.data = {
            "name": "Paris",
            "feature_name": "city",
            "country_name": "France",
            "admin1_name": "Île-de-France",
        }

        # Act
        description = resolver._generate_description(mock_candidate)

        # Assert
        assert "Paris" in description
        assert "city" in description
        assert "France" in description

    @patch("geoparser.modules.resolvers.sentencetransformer.spacy.load")
    @patch(
        "geoparser.modules.resolvers.sentencetransformer.AutoTokenizer.from_pretrained"
    )
    @patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer")
    @patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer")
    def test_calculate_similarities_returns_list_of_floats(
        self, mock_gazetteer, mock_transformer, mock_tokenizer, mock_spacy_load
    ):
        """Test that _calculate_similarities returns list of similarity scores."""
        # Arrange
        from geoparser.modules.resolvers.sentencetransformer import (
            SentenceTransformerResolver,
        )

        resolver = SentenceTransformerResolver()

        context_embedding = torch.tensor([1.0, 0.0, 0.0])
        candidate_embeddings = [
            torch.tensor([1.0, 0.0, 0.0]),  # Perfect match
            torch.tensor([0.0, 1.0, 0.0]),  # Orthogonal
        ]

        # Act
        similarities = resolver._calculate_similarities(
            context_embedding, candidate_embeddings
        )

        # Assert
        assert isinstance(similarities, list)
        assert len(similarities) == 2
        assert all(isinstance(s, float) for s in similarities)
        # First should be higher similarity than second
        assert similarities[0] > similarities[1]

    @patch("geoparser.modules.resolvers.sentencetransformer.spacy.load")
    @patch(
        "geoparser.modules.resolvers.sentencetransformer.AutoTokenizer.from_pretrained"
    )
    @patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer")
    @patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer")
    def test_calculate_similarities_handles_empty_list(
        self, mock_gazetteer, mock_transformer, mock_tokenizer, mock_spacy_load
    ):
        """Test that _calculate_similarities handles empty candidate list."""
        # Arrange
        from geoparser.modules.resolvers.sentencetransformer import (
            SentenceTransformerResolver,
        )

        resolver = SentenceTransformerResolver()

        context_embedding = torch.tensor([1.0, 0.0, 0.0])
        candidate_embeddings = []

        # Act
        similarities = resolver._calculate_similarities(
            context_embedding, candidate_embeddings
        )

        # Assert
        assert similarities == []
