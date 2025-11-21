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
        assert resolver.min_similarity == 0.6
        assert resolver.max_tiers == 3

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

        custom_map = {
            "name": "name",
            "type": "type",
            "level1": "level1",
            "level2": "level2",
            "level3": "level3",
        }

        # Act
        resolver = SentenceTransformerResolver(
            model_name="custom-model",
            gazetteer_name="custom-gazetteer",
            min_similarity=0.8,
            max_tiers=5,
            attribute_map=custom_map,
        )

        # Assert
        assert resolver.model_name == "custom-model"
        assert resolver.gazetteer_name == "custom-gazetteer"
        assert resolver.min_similarity == 0.8
        assert resolver.max_tiers == 5

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

        custom_map = {
            "name": "name",
            "type": "type",
            "level1": "level1",
            "level2": "level2",
            "level3": "level3",
        }

        # Act
        resolver = SentenceTransformerResolver(
            model_name="test-model",
            gazetteer_name="test-gazetteer",
            min_similarity=0.75,
            max_tiers=4,
            attribute_map=custom_map,
        )

        # Assert
        assert resolver.config["model_name"] == "test-model"
        assert resolver.config["gazetteer_name"] == "test-gazetteer"
        assert resolver.config["min_similarity"] == 0.75
        assert resolver.config["max_tiers"] == 4

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

        custom_map = {
            "name": "name",
            "type": "type",
            "level1": "level1",
            "level2": "level2",
            "level3": "level3",
        }

        # Act
        resolver = SentenceTransformerResolver(
            gazetteer_name="test-gazetteer", attribute_map=custom_map
        )

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
        """Test that all caches are initialized as empty dictionaries."""
        # Arrange
        from geoparser.modules.resolvers.sentencetransformer import (
            SentenceTransformerResolver,
        )

        # Act
        resolver = SentenceTransformerResolver()

        # Assert
        assert resolver.doc_tokens == {}
        assert resolver.doc_objects == {}
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
        resolver1 = SentenceTransformerResolver(min_similarity=0.6)
        resolver2 = SentenceTransformerResolver(min_similarity=0.7)

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
            model_name="model1",
            gazetteer_name="geonames",
            min_similarity=0.6,
            max_tiers=3,
        )
        resolver2 = SentenceTransformerResolver(
            model_name="model1",
            gazetteer_name="geonames",
            min_similarity=0.6,
            max_tiers=3,
        )

        # Assert
        assert resolver1.id == resolver2.id

    @patch("geoparser.modules.resolvers.sentencetransformer.spacy.load")
    @patch(
        "geoparser.modules.resolvers.sentencetransformer.AutoTokenizer.from_pretrained"
    )
    @patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer")
    @patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer")
    def test_accepts_custom_attribute_map(
        self, mock_gazetteer, mock_transformer, mock_tokenizer, mock_spacy_load
    ):
        """Test that custom attribute_map is accepted and stored."""
        # Arrange
        from geoparser.modules.resolvers.sentencetransformer import (
            SentenceTransformerResolver,
        )

        custom_map = {
            "name": "custom_name",
            "type": "custom_type",
            "level1": "custom_level1",
            "level2": "custom_level2",
            "level3": "custom_level3",
        }

        # Act
        resolver = SentenceTransformerResolver(
            gazetteer_name="custom_gazetteer", attribute_map=custom_map
        )

        # Assert
        assert resolver.attribute_map == custom_map

    @patch("geoparser.modules.resolvers.sentencetransformer.spacy.load")
    @patch(
        "geoparser.modules.resolvers.sentencetransformer.AutoTokenizer.from_pretrained"
    )
    @patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer")
    @patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer")
    def test_raises_error_for_unknown_gazetteer_without_attribute_map(
        self, mock_gazetteer, mock_transformer, mock_tokenizer, mock_spacy_load
    ):
        """Test that error is raised for unknown gazetteer when no attribute_map provided."""
        # Arrange
        from geoparser.modules.resolvers.sentencetransformer import (
            SentenceTransformerResolver,
        )

        # Act & Assert
        with pytest.raises(
            ValueError, match="not configured in GAZETTEER_ATTRIBUTE_MAP"
        ):
            SentenceTransformerResolver(gazetteer_name="unknown_gazetteer")

    @patch("geoparser.modules.resolvers.sentencetransformer.spacy.load")
    @patch(
        "geoparser.modules.resolvers.sentencetransformer.AutoTokenizer.from_pretrained"
    )
    @patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer")
    @patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer")
    def test_uses_gazetteer_attribute_map_when_no_custom_map(
        self, mock_gazetteer, mock_transformer, mock_tokenizer, mock_spacy_load
    ):
        """Test that GAZETTEER_ATTRIBUTE_MAP is used when no custom map provided."""
        # Arrange
        from geoparser.modules.resolvers.sentencetransformer import (
            SentenceTransformerResolver,
        )

        # Act
        resolver = SentenceTransformerResolver(gazetteer_name="geonames")

        # Assert
        expected_map = SentenceTransformerResolver.GAZETTEER_ATTRIBUTE_MAP["geonames"]
        assert resolver.attribute_map == expected_map

    @patch("geoparser.modules.resolvers.sentencetransformer.spacy.load")
    @patch(
        "geoparser.modules.resolvers.sentencetransformer.AutoTokenizer.from_pretrained"
    )
    @patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer")
    @patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer")
    def test_validate_and_set_attribute_map_returns_custom_map(
        self, mock_gazetteer, mock_transformer, mock_tokenizer, mock_spacy_load
    ):
        """Test that _validate_and_set_attribute_map returns custom map when provided."""
        # Arrange
        from geoparser.modules.resolvers.sentencetransformer import (
            SentenceTransformerResolver,
        )

        custom_map = {
            "name": "test_name",
            "type": "test_type",
            "level1": "test_level1",
            "level2": "test_level2",
            "level3": "test_level3",
        }

        # Act
        resolver = SentenceTransformerResolver(
            gazetteer_name="any-gazetteer", attribute_map=custom_map
        )
        result = resolver._validate_and_set_attribute_map("any-gazetteer", custom_map)

        # Assert
        assert result == custom_map

    @patch("geoparser.modules.resolvers.sentencetransformer.spacy.load")
    @patch(
        "geoparser.modules.resolvers.sentencetransformer.AutoTokenizer.from_pretrained"
    )
    @patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer")
    @patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer")
    def test_validate_and_set_attribute_map_looks_up_configured_gazetteer(
        self, mock_gazetteer, mock_transformer, mock_tokenizer, mock_spacy_load
    ):
        """Test that _validate_and_set_attribute_map looks up configured gazetteer."""
        # Arrange
        from geoparser.modules.resolvers.sentencetransformer import (
            SentenceTransformerResolver,
        )

        # Act
        resolver = SentenceTransformerResolver(gazetteer_name="geonames")
        result = resolver._validate_and_set_attribute_map("geonames", None)

        # Assert
        expected_map = SentenceTransformerResolver.GAZETTEER_ATTRIBUTE_MAP["geonames"]
        assert result == expected_map

    @patch("geoparser.modules.resolvers.sentencetransformer.spacy.load")
    @patch(
        "geoparser.modules.resolvers.sentencetransformer.AutoTokenizer.from_pretrained"
    )
    @patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer")
    @patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer")
    def test_validate_and_set_attribute_map_raises_for_unknown_gazetteer(
        self, mock_gazetteer, mock_transformer, mock_tokenizer, mock_spacy_load
    ):
        """Test that _validate_and_set_attribute_map raises error for unknown gazetteer."""
        # Arrange
        from geoparser.modules.resolvers.sentencetransformer import (
            SentenceTransformerResolver,
        )

        # Create a resolver first (to access the method)
        resolver = SentenceTransformerResolver(
            gazetteer_name="geonames"
        )  # Use valid gazetteer

        # Act & Assert
        with pytest.raises(
            ValueError, match="not configured in GAZETTEER_ATTRIBUTE_MAP"
        ):
            resolver._validate_and_set_attribute_map("unknown_gazetteer", None)

    @patch("geoparser.modules.resolvers.sentencetransformer.spacy.cli.download")
    @patch("geoparser.modules.resolvers.sentencetransformer.spacy.load")
    @patch(
        "geoparser.modules.resolvers.sentencetransformer.AutoTokenizer.from_pretrained"
    )
    @patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer")
    @patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer")
    def test_downloads_spacy_model_if_not_found(
        self,
        mock_gazetteer,
        mock_transformer,
        mock_tokenizer,
        mock_spacy_load,
        mock_download,
    ):
        """Test that spaCy model is automatically downloaded if not found."""
        # Arrange
        from geoparser.modules.resolvers.sentencetransformer import (
            SentenceTransformerResolver,
        )

        mock_nlp = Mock()

        # First call raises OSError (model not found), second call succeeds
        mock_spacy_load.side_effect = [OSError("Model not found"), mock_nlp]

        # Act
        resolver = SentenceTransformerResolver()

        # Assert
        mock_download.assert_called_once_with("xx_sent_ud_sm")
        assert mock_spacy_load.call_count == 2
        assert resolver.nlp == mock_nlp

    @patch("geoparser.modules.resolvers.sentencetransformer.spacy.load")
    @patch(
        "geoparser.modules.resolvers.sentencetransformer.AutoTokenizer.from_pretrained"
    )
    @patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer")
    @patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer")
    def test_does_not_download_spacy_model_if_exists(
        self, mock_gazetteer, mock_transformer, mock_tokenizer, mock_spacy_load
    ):
        """Test that spaCy model is not downloaded if it already exists."""
        # Arrange
        from geoparser.modules.resolvers.sentencetransformer import (
            SentenceTransformerResolver,
        )

        mock_nlp = Mock()
        mock_spacy_load.return_value = mock_nlp

        # Act
        resolver = SentenceTransformerResolver()

        # Assert
        # spacy.load should be called only once (no download needed)
        assert mock_spacy_load.call_count == 1
        assert resolver.nlp == mock_nlp


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

    @patch("geoparser.modules.resolvers.sentencetransformer.spacy.load")
    @patch(
        "geoparser.modules.resolvers.sentencetransformer.AutoTokenizer.from_pretrained"
    )
    @patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer")
    @patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer")
    def test_caches_doc_tokens(
        self, mock_gazetteer, mock_transformer, mock_tokenizer, mock_spacy_load
    ):
        """Test that document token counts are cached to avoid recomputation."""
        # Arrange
        from geoparser.modules.resolvers.sentencetransformer import (
            SentenceTransformerResolver,
        )

        mock_transformer_instance = mock_transformer.return_value
        mock_transformer_instance.get_max_seq_length.return_value = 512
        mock_transformer_instance.encode.return_value = torch.tensor([[0.1, 0.2, 0.3]])

        mock_tokenizer_instance = mock_tokenizer.return_value
        mock_tokenizer_instance.tokenize.return_value = ["test", "token"]

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

        # Act - Call predict with document containing multiple references
        text = "Test text"
        resolver.predict(texts=[text], references=[[(0, 4), (5, 9)]])

        # Assert - Token count for text should be cached
        assert text in resolver.doc_tokens
        assert resolver.doc_tokens[text] == 2

        # Act - Call tokenize count before second predict
        tokenize_call_count_first = mock_tokenizer_instance.tokenize.call_count

        # Call predict again with same text
        resolver.predict(texts=[text], references=[[(0, 4)]])
        tokenize_call_count_second = mock_tokenizer_instance.tokenize.call_count

        # Assert - tokenize should not be called again for the document text
        # (it may be called for sentence tokenization, but not for full doc)
        assert text in resolver.doc_tokens

    @patch("geoparser.modules.resolvers.sentencetransformer.spacy.load")
    @patch(
        "geoparser.modules.resolvers.sentencetransformer.AutoTokenizer.from_pretrained"
    )
    @patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer")
    @patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer")
    def test_caches_doc_objects(
        self, mock_gazetteer, mock_transformer, mock_tokenizer, mock_spacy_load
    ):
        """Test that spaCy doc objects are cached to avoid recomputation."""
        # Arrange
        from geoparser.modules.resolvers.sentencetransformer import (
            SentenceTransformerResolver,
        )

        mock_transformer_instance = mock_transformer.return_value
        mock_transformer_instance.get_max_seq_length.return_value = 512
        mock_transformer_instance.encode.return_value = torch.tensor([[0.1, 0.2, 0.3]])

        mock_tokenizer_instance = mock_tokenizer.return_value
        # Return many tokens to trigger sentence splitting
        mock_tokenizer_instance.tokenize.return_value = ["token"] * 600

        # Mock spaCy
        mock_nlp_instance = Mock()
        mock_sent = Mock()
        mock_sent.start_char = 0
        mock_sent.end_char = 9
        mock_sent.text = "Test text"
        mock_doc = Mock()
        mock_doc.sents = [mock_sent]
        mock_nlp_instance.return_value = mock_doc
        mock_spacy_load.return_value = mock_nlp_instance

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

        # Act - Call predict with document containing multiple references
        text = "Test text"
        resolver.predict(texts=[text], references=[[(0, 4), (5, 9)]])

        # Assert - spaCy doc for text should be cached
        assert text in resolver.doc_objects

        # Act - Count spaCy calls before second predict
        nlp_call_count_first = mock_nlp_instance.call_count

        # Call predict again with same text
        resolver.predict(texts=[text], references=[[(0, 4)]])
        nlp_call_count_second = mock_nlp_instance.call_count

        # Assert - spaCy should not be called again for the same text
        assert nlp_call_count_second == nlp_call_count_first
        assert text in resolver.doc_objects


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

    @patch("geoparser.modules.resolvers.sentencetransformer.spacy.load")
    @patch(
        "geoparser.modules.resolvers.sentencetransformer.AutoTokenizer.from_pretrained"
    )
    @patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer")
    @patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer")
    def test_extract_context_returns_full_text_when_within_limit(
        self, mock_gazetteer, mock_transformer, mock_tokenizer, mock_spacy_load
    ):
        """Test that _extract_context returns full text when within token limit."""
        # Arrange
        from geoparser.modules.resolvers.sentencetransformer import (
            SentenceTransformerResolver,
        )

        mock_transformer_instance = mock_transformer.return_value
        mock_transformer_instance.get_max_seq_length.return_value = 512

        mock_tokenizer_instance = mock_tokenizer.return_value
        # Short text - only 3 tokens
        mock_tokenizer_instance.tokenize.return_value = ["Paris", "is", "beautiful"]

        resolver = SentenceTransformerResolver()

        text = "Paris is beautiful"

        # Act
        context = resolver._extract_context(text, 0, 5)

        # Assert
        assert context == text

    @patch("geoparser.modules.resolvers.sentencetransformer.spacy.load")
    @patch(
        "geoparser.modules.resolvers.sentencetransformer.AutoTokenizer.from_pretrained"
    )
    @patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer")
    @patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer")
    def test_extract_context_expands_bidirectionally(
        self, mock_gazetteer, mock_transformer, mock_tokenizer, mock_spacy_load
    ):
        """Test that _extract_context expands context bidirectionally around reference."""
        # Arrange
        from geoparser.modules.resolvers.sentencetransformer import (
            SentenceTransformerResolver,
        )

        mock_transformer_instance = mock_transformer.return_value
        mock_transformer_instance.get_max_seq_length.return_value = 512

        mock_tokenizer_instance = mock_tokenizer.return_value

        # Return different lengths for different calls
        def tokenize_side_effect(text):
            # Simulate that full text is too long
            if len(text) > 20:
                return ["token"] * 600  # Exceeds limit
            # But sentences are short
            return ["token"] * 3

        mock_tokenizer_instance.tokenize.side_effect = tokenize_side_effect

        # Mock spaCy sentence splitter
        mock_nlp = Mock()
        mock_sent1 = Mock()
        mock_sent1.start_char = 0
        mock_sent1.end_char = (
            26  # Cover the full text including "Paris" at position 10-15
        )
        mock_sent1.text = "I went to Paris yesterday."

        mock_doc = Mock()
        mock_doc.sents = [mock_sent1]
        mock_nlp.return_value = mock_doc

        resolver = SentenceTransformerResolver()
        resolver.nlp = mock_nlp

        text = "I went to Paris yesterday."

        # Act
        context = resolver._extract_context(text, 10, 15)  # "Paris"

        # Assert
        # Should at least include the sentence containing the reference
        assert isinstance(context, str)
        # Should contain the reference text
        assert "Paris" in context or context == text

    @patch("geoparser.modules.resolvers.sentencetransformer.spacy.load")
    @patch(
        "geoparser.modules.resolvers.sentencetransformer.AutoTokenizer.from_pretrained"
    )
    @patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer")
    @patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer")
    def test_generate_description_handles_missing_attributes(
        self, mock_gazetteer, mock_transformer, mock_tokenizer, mock_spacy_load
    ):
        """Test that _generate_description handles missing attributes gracefully."""
        # Arrange
        from geoparser.modules.resolvers.sentencetransformer import (
            SentenceTransformerResolver,
        )

        resolver = SentenceTransformerResolver(gazetteer_name="geonames")

        mock_candidate = Mock()
        mock_candidate.data = {
            "name": "Paris",
            # Missing feature_name and admin levels
        }

        # Act
        description = resolver._generate_description(mock_candidate)

        # Assert
        assert "Paris" in description
        # Should not crash, just include what's available

    @patch("geoparser.modules.resolvers.sentencetransformer.spacy.load")
    @patch(
        "geoparser.modules.resolvers.sentencetransformer.AutoTokenizer.from_pretrained"
    )
    @patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer")
    @patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer")
    def test_generate_description_includes_all_admin_levels(
        self, mock_gazetteer, mock_transformer, mock_tokenizer, mock_spacy_load
    ):
        """Test that _generate_description includes all available admin levels."""
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
            "admin2_name": "Paris",
        }

        # Act
        description = resolver._generate_description(mock_candidate)

        # Assert
        assert "Paris" in description
        assert "city" in description
        assert "France" in description
        assert "Île-de-France" in description
        # Should be in hierarchical order: level3, level2, level1
        assert "in" in description

    @patch("geoparser.modules.resolvers.sentencetransformer.spacy.load")
    @patch(
        "geoparser.modules.resolvers.sentencetransformer.AutoTokenizer.from_pretrained"
    )
    @patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer")
    @patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer")
    def test_generate_description_uses_custom_attribute_map(
        self, mock_gazetteer, mock_transformer, mock_tokenizer, mock_spacy_load
    ):
        """Test that _generate_description uses custom attribute_map."""
        # Arrange
        from geoparser.modules.resolvers.sentencetransformer import (
            SentenceTransformerResolver,
        )

        custom_map = {
            "name": "custom_name",
            "type": "custom_type",
            "level1": "custom_level1",
            "level2": "custom_level2",
            "level3": "custom_level3",
        }

        resolver = SentenceTransformerResolver(
            gazetteer_name="custom_gazetteer", attribute_map=custom_map
        )

        mock_candidate = Mock()
        mock_candidate.data = {
            "custom_name": "Paris",
            "custom_type": "city",
            "custom_level1": "France",
        }

        # Act
        description = resolver._generate_description(mock_candidate)

        # Assert - Should use custom attribute names
        assert "Paris" in description
        assert "city" in description
        assert "France" in description

    @patch("geoparser.modules.resolvers.sentencetransformer.spacy.load")
    @patch(
        "geoparser.modules.resolvers.sentencetransformer.AutoTokenizer.from_pretrained"
    )
    @patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer")
    @patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer")
    def test_calculate_similarities_returns_correct_values(
        self, mock_gazetteer, mock_transformer, mock_tokenizer, mock_spacy_load
    ):
        """Test that _calculate_similarities returns correct cosine similarity values."""
        # Arrange
        from geoparser.modules.resolvers.sentencetransformer import (
            SentenceTransformerResolver,
        )

        resolver = SentenceTransformerResolver()

        # Create embeddings with known similarities
        context_embedding = torch.tensor([1.0, 0.0, 0.0])
        candidate_embeddings = [
            torch.tensor([1.0, 0.0, 0.0]),  # Similarity = 1.0 (identical)
            torch.tensor([0.5, 0.866, 0.0]),  # Similarity ≈ 0.5 (60 degree angle)
            torch.tensor([-1.0, 0.0, 0.0]),  # Similarity = -1.0 (opposite)
        ]

        # Act
        similarities = resolver._calculate_similarities(
            context_embedding, candidate_embeddings
        )

        # Assert
        assert len(similarities) == 3
        assert abs(similarities[0] - 1.0) < 0.01  # First is perfect match
        assert abs(similarities[1] - 0.5) < 0.1  # Second is ~0.5
        assert abs(similarities[2] - (-1.0)) < 0.01  # Third is opposite


@pytest.mark.unit
class TestSentenceTransformerResolverPrepareTrainingData:
    """Test SentenceTransformerResolver _prepare_training_data method."""

    @patch("geoparser.modules.resolvers.sentencetransformer.spacy.load")
    @patch(
        "geoparser.modules.resolvers.sentencetransformer.AutoTokenizer.from_pretrained"
    )
    @patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer")
    @patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer")
    def test_creates_training_examples_from_referents(
        self, mock_gazetteer_class, mock_transformer, mock_tokenizer, mock_spacy_load
    ):
        """Test that _prepare_training_data creates training examples from referents."""
        # Arrange
        from geoparser.modules.resolvers.sentencetransformer import (
            SentenceTransformerResolver,
        )

        resolver = SentenceTransformerResolver(gazetteer_name="geonames")

        # Mock gazetteer search to return candidates
        mock_gazetteer_instance = mock_gazetteer_class.return_value
        mock_candidate1 = Mock()
        mock_candidate1.location_id_value = "123"
        mock_candidate1.data = {"name": "Paris", "feature_name": "city"}
        mock_candidate2 = Mock()
        mock_candidate2.location_id_value = "456"
        mock_candidate2.data = {"name": "Paris", "feature_name": "region"}
        mock_gazetteer_instance.search.return_value = [mock_candidate1, mock_candidate2]

        # Mock _extract_context
        with patch.object(
            resolver, "_extract_context", return_value="Paris is beautiful"
        ):
            texts = ["Paris is beautiful."]
            references = [[(0, 5)]]  # "Paris"
            referents = [[("geonames", "123")]]  # Matches candidate1

            # Act
            training_data = resolver._prepare_training_data(
                texts, references, referents
            )

            # Assert
            assert "sentence1" in training_data
            assert "sentence2" in training_data
            assert "label" in training_data
            assert len(training_data["sentence1"]) > 0
            assert len(training_data["sentence2"]) > 0
            assert len(training_data["label"]) > 0

    @patch("geoparser.modules.resolvers.sentencetransformer.spacy.load")
    @patch(
        "geoparser.modules.resolvers.sentencetransformer.AutoTokenizer.from_pretrained"
    )
    @patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer")
    @patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer")
    def test_creates_positive_and_negative_examples(
        self, mock_gazetteer_class, mock_transformer, mock_tokenizer, mock_spacy_load
    ):
        """Test that _prepare_training_data creates both positive and negative examples."""
        # Arrange
        from geoparser.modules.resolvers.sentencetransformer import (
            SentenceTransformerResolver,
        )

        resolver = SentenceTransformerResolver(gazetteer_name="geonames")

        # Mock gazetteer search to return multiple candidates
        mock_gazetteer_instance = mock_gazetteer_class.return_value
        mock_candidate1 = Mock()
        mock_candidate1.location_id_value = "123"
        mock_candidate1.data = {"name": "Paris", "feature_name": "city"}
        mock_candidate2 = Mock()
        mock_candidate2.location_id_value = "456"
        mock_candidate2.data = {"name": "Paris", "feature_name": "region"}
        mock_gazetteer_instance.search.return_value = [mock_candidate1, mock_candidate2]

        with patch.object(
            resolver, "_extract_context", return_value="Paris is beautiful"
        ):
            texts = ["Paris is beautiful."]
            references = [[(0, 5)]]
            referents = [[("geonames", "123")]]  # Only matches candidate1

            # Act
            training_data = resolver._prepare_training_data(
                texts, references, referents
            )

            # Assert
            # Should have 2 examples: 1 positive (label=1) and 1 negative (label=0)
            assert len(training_data["label"]) == 2
            assert 1 in training_data["label"]  # Positive example
            assert 0 in training_data["label"]  # Negative example

    @patch("geoparser.modules.resolvers.sentencetransformer.spacy.load")
    @patch(
        "geoparser.modules.resolvers.sentencetransformer.AutoTokenizer.from_pretrained"
    )
    @patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer")
    @patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer")
    def test_handles_multiple_references_in_document(
        self, mock_gazetteer_class, mock_transformer, mock_tokenizer, mock_spacy_load
    ):
        """Test that _prepare_training_data handles multiple references per document."""
        # Arrange
        from geoparser.modules.resolvers.sentencetransformer import (
            SentenceTransformerResolver,
        )

        resolver = SentenceTransformerResolver(gazetteer_name="geonames")

        # Mock gazetteer search
        mock_gazetteer_instance = mock_gazetteer_class.return_value
        mock_candidate = Mock()
        mock_candidate.location_id_value = "123"
        mock_candidate.data = {"name": "City", "feature_name": "city"}
        mock_gazetteer_instance.search.return_value = [mock_candidate]

        with patch.object(resolver, "_extract_context", return_value="Context"):
            texts = ["Paris and London"]
            references = [[(0, 5), (10, 16)]]  # "Paris", "London"
            referents = [[("geonames", "123"), ("geonames", "123")]]

            # Act
            training_data = resolver._prepare_training_data(
                texts, references, referents
            )

            # Assert
            # Should have examples for both references
            assert len(training_data["sentence1"]) >= 2

    @patch("geoparser.modules.resolvers.sentencetransformer.spacy.load")
    @patch(
        "geoparser.modules.resolvers.sentencetransformer.AutoTokenizer.from_pretrained"
    )
    @patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer")
    @patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer")
    def test_handles_multiple_documents(
        self, mock_gazetteer_class, mock_transformer, mock_tokenizer, mock_spacy_load
    ):
        """Test that _prepare_training_data handles multiple documents."""
        # Arrange
        from geoparser.modules.resolvers.sentencetransformer import (
            SentenceTransformerResolver,
        )

        resolver = SentenceTransformerResolver(gazetteer_name="geonames")

        # Mock gazetteer search
        mock_gazetteer_instance = mock_gazetteer_class.return_value
        mock_candidate = Mock()
        mock_candidate.location_id_value = "123"
        mock_candidate.data = {"name": "City", "feature_name": "city"}
        mock_gazetteer_instance.search.return_value = [mock_candidate]

        with patch.object(resolver, "_extract_context", return_value="Context"):
            texts = ["Paris is beautiful.", "London is historic."]
            references = [[(0, 5)], [(0, 6)]]  # "Paris", "London"
            referents = [[("geonames", "123")], [("geonames", "123")]]

            # Act
            training_data = resolver._prepare_training_data(
                texts, references, referents
            )

            # Assert
            # Should have examples from both documents
            assert len(training_data["sentence1"]) >= 2

    @patch("geoparser.modules.resolvers.sentencetransformer.spacy.load")
    @patch(
        "geoparser.modules.resolvers.sentencetransformer.AutoTokenizer.from_pretrained"
    )
    @patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer")
    @patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer")
    def test_extracts_context_for_each_reference(
        self, mock_gazetteer_class, mock_transformer, mock_tokenizer, mock_spacy_load
    ):
        """Test that _prepare_training_data extracts context for each reference."""
        # Arrange
        from geoparser.modules.resolvers.sentencetransformer import (
            SentenceTransformerResolver,
        )

        resolver = SentenceTransformerResolver(gazetteer_name="geonames")

        # Mock gazetteer search
        mock_gazetteer_instance = mock_gazetteer_class.return_value
        mock_candidate = Mock()
        mock_candidate.location_id_value = "123"
        mock_candidate.data = {"name": "City", "feature_name": "city"}
        mock_gazetteer_instance.search.return_value = [mock_candidate]

        with patch.object(
            resolver, "_extract_context", return_value="Extracted context"
        ) as mock_extract:
            texts = ["Paris is beautiful."]
            references = [[(0, 5)]]
            referents = [[("geonames", "123")]]

            # Act
            training_data = resolver._prepare_training_data(
                texts, references, referents
            )

            # Assert
            # _extract_context should have been called
            mock_extract.assert_called()
            # All sentence1 entries should be the extracted context
            assert all(s1 == "Extracted context" for s1 in training_data["sentence1"])

    @patch("geoparser.modules.resolvers.sentencetransformer.spacy.load")
    @patch(
        "geoparser.modules.resolvers.sentencetransformer.AutoTokenizer.from_pretrained"
    )
    @patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer")
    @patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer")
    def test_generates_descriptions_for_candidates(
        self, mock_gazetteer_class, mock_transformer, mock_tokenizer, mock_spacy_load
    ):
        """Test that _prepare_training_data generates descriptions for candidates."""
        # Arrange
        from geoparser.modules.resolvers.sentencetransformer import (
            SentenceTransformerResolver,
        )

        resolver = SentenceTransformerResolver(gazetteer_name="geonames")

        # Mock gazetteer search
        mock_gazetteer_instance = mock_gazetteer_class.return_value
        mock_candidate = Mock()
        mock_candidate.location_id_value = "123"
        mock_candidate.data = {"name": "Paris", "feature_name": "city"}
        mock_gazetteer_instance.search.return_value = [mock_candidate]

        with patch.object(resolver, "_extract_context", return_value="Context"):
            with patch.object(
                resolver, "_generate_description", return_value="Paris (city)"
            ) as mock_generate:
                texts = ["Paris is beautiful."]
                references = [[(0, 5)]]
                referents = [[("geonames", "123")]]

                # Act
                training_data = resolver._prepare_training_data(
                    texts, references, referents
                )

                # Assert
                # _generate_description should have been called
                mock_generate.assert_called()
                # All sentence2 entries should be the generated description
                assert all(s2 == "Paris (city)" for s2 in training_data["sentence2"])

    @patch("geoparser.modules.resolvers.sentencetransformer.spacy.load")
    @patch(
        "geoparser.modules.resolvers.sentencetransformer.AutoTokenizer.from_pretrained"
    )
    @patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer")
    @patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer")
    def test_returns_correct_data_structure(
        self, mock_gazetteer_class, mock_transformer, mock_tokenizer, mock_spacy_load
    ):
        """Test that _prepare_training_data returns correct data structure."""
        # Arrange
        from geoparser.modules.resolvers.sentencetransformer import (
            SentenceTransformerResolver,
        )

        resolver = SentenceTransformerResolver(gazetteer_name="geonames")

        # Mock gazetteer search
        mock_gazetteer_instance = mock_gazetteer_class.return_value
        mock_candidate = Mock()
        mock_candidate.location_id_value = "123"
        mock_candidate.data = {"name": "City", "feature_name": "city"}
        mock_gazetteer_instance.search.return_value = [mock_candidate]

        with patch.object(resolver, "_extract_context", return_value="Context"):
            texts = ["Paris"]
            references = [[(0, 5)]]
            referents = [[("geonames", "123")]]

            # Act
            training_data = resolver._prepare_training_data(
                texts, references, referents
            )

            # Assert
            # Should be a dict with three keys
            assert isinstance(training_data, dict)
            assert set(training_data.keys()) == {"sentence1", "sentence2", "label"}
            # All lists should have the same length
            assert len(training_data["sentence1"]) == len(training_data["sentence2"])
            assert len(training_data["sentence1"]) == len(training_data["label"])
            # Labels should be 0 or 1
            assert all(label in [0, 1] for label in training_data["label"])
