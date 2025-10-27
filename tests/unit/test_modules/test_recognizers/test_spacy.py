"""
Unit tests for geoparser/modules/recognizers/spacy.py

Tests the SpacyRecognizer module with mocked spaCy models.
"""

from unittest.mock import Mock, patch

import pytest

from geoparser.modules.recognizers.spacy import SpacyRecognizer


@pytest.mark.unit
class TestSpacyRecognizerInitialization:
    """Test SpacyRecognizer initialization."""

    @patch("geoparser.modules.recognizers.spacy.spacy.load")
    def test_creates_with_default_parameters(self, mock_spacy_load):
        """Test that SpacyRecognizer can be created with default parameters."""
        # Arrange
        mock_nlp = Mock()
        mock_nlp.pipe_names = []
        mock_spacy_load.return_value = mock_nlp

        # Act
        recognizer = SpacyRecognizer()

        # Assert
        assert recognizer.name == "SpacyRecognizer"
        assert recognizer.model_name == "en_core_web_sm"
        assert recognizer.entity_types == {"FAC", "GPE", "LOC"}

    @patch("geoparser.modules.recognizers.spacy.spacy.load")
    def test_creates_with_custom_model_name(self, mock_spacy_load):
        """Test that SpacyRecognizer can be created with custom model name."""
        # Arrange
        mock_nlp = Mock()
        mock_nlp.pipe_names = []
        mock_spacy_load.return_value = mock_nlp

        # Act
        recognizer = SpacyRecognizer(model_name="en_core_web_lg")

        # Assert
        assert recognizer.model_name == "en_core_web_lg"
        mock_spacy_load.assert_called_once_with("en_core_web_lg")

    @patch("geoparser.modules.recognizers.spacy.spacy.load")
    def test_creates_with_custom_entity_types(self, mock_spacy_load):
        """Test that SpacyRecognizer can be created with custom entity types."""
        # Arrange
        mock_nlp = Mock()
        mock_nlp.pipe_names = []
        mock_spacy_load.return_value = mock_nlp

        # Act
        recognizer = SpacyRecognizer(entity_types=["GPE"])

        # Assert
        assert recognizer.entity_types == {"GPE"}

    @patch("geoparser.modules.recognizers.spacy.spacy.load")
    def test_converts_entity_types_to_set(self, mock_spacy_load):
        """Test that entity_types list is converted to set for efficient lookups."""
        # Arrange
        mock_nlp = Mock()
        mock_nlp.pipe_names = []
        mock_spacy_load.return_value = mock_nlp

        # Act
        recognizer = SpacyRecognizer(entity_types=["GPE", "LOC"])

        # Assert
        assert isinstance(recognizer.entity_types, set)

    @patch("geoparser.modules.recognizers.spacy.spacy.load")
    def test_config_contains_model_and_entity_types(self, mock_spacy_load):
        """Test that config stores model_name and entity_types."""
        # Arrange
        mock_nlp = Mock()
        mock_nlp.pipe_names = []
        mock_spacy_load.return_value = mock_nlp

        # Act
        recognizer = SpacyRecognizer(
            model_name="en_core_web_sm", entity_types=["GPE", "LOC"]
        )

        # Assert
        assert recognizer.config["model_name"] == "en_core_web_sm"
        assert recognizer.config["entity_types"] == ["GPE", "LOC"]

    @patch("geoparser.modules.recognizers.spacy.spacy.load")
    def test_removes_non_ner_pipeline_components(self, mock_spacy_load):
        """Test that non-NER pipeline components are removed for optimization."""
        # Arrange
        mock_nlp = Mock()
        mock_nlp.pipe_names = ["tagger", "parser", "ner", "lemmatizer"]
        mock_spacy_load.return_value = mock_nlp

        # Act
        recognizer = SpacyRecognizer()

        # Assert
        # Should remove tagger, parser, lemmatizer but keep ner
        assert mock_nlp.remove_pipe.call_count == 3
        removed_pipes = [call[0][0] for call in mock_nlp.remove_pipe.call_args_list]
        assert "tagger" in removed_pipes
        assert "parser" in removed_pipes
        assert "lemmatizer" in removed_pipes

    @patch("geoparser.modules.recognizers.spacy.spacy.load")
    def test_only_removes_existing_pipeline_components(self, mock_spacy_load):
        """Test that only existing pipeline components are removed."""
        # Arrange
        mock_nlp = Mock()
        mock_nlp.pipe_names = ["ner"]  # Only NER, no other components
        mock_spacy_load.return_value = mock_nlp

        # Act
        recognizer = SpacyRecognizer()

        # Assert
        # Should not call remove_pipe since no unnecessary components exist
        mock_nlp.remove_pipe.assert_not_called()

    @patch("geoparser.modules.recognizers.spacy.spacy.load")
    def test_different_configs_produce_different_ids(self, mock_spacy_load):
        """Test that different configurations produce different module IDs."""
        # Arrange
        mock_nlp = Mock()
        mock_nlp.pipe_names = []
        mock_spacy_load.return_value = mock_nlp

        # Act
        recognizer1 = SpacyRecognizer(model_name="en_core_web_sm", entity_types=["GPE"])
        recognizer2 = SpacyRecognizer(model_name="en_core_web_sm", entity_types=["LOC"])

        # Assert
        assert recognizer1.id != recognizer2.id

    @patch("geoparser.modules.recognizers.spacy.spacy.load")
    def test_same_config_produces_same_id(self, mock_spacy_load):
        """Test that same configuration produces same module ID."""
        # Arrange
        mock_nlp = Mock()
        mock_nlp.pipe_names = []
        mock_spacy_load.return_value = mock_nlp

        # Act
        recognizer1 = SpacyRecognizer(
            model_name="en_core_web_sm", entity_types=["GPE", "LOC"]
        )
        recognizer2 = SpacyRecognizer(
            model_name="en_core_web_sm", entity_types=["GPE", "LOC"]
        )

        # Assert
        assert recognizer1.id == recognizer2.id


@pytest.mark.unit
class TestSpacyRecognizerPredict:
    """Test SpacyRecognizer predict method."""

    @patch("geoparser.modules.recognizers.spacy.spacy.load")
    def test_calls_nlp_pipe_with_texts(self, mock_spacy_load):
        """Test that predict calls nlp.pipe with input texts."""
        # Arrange
        mock_nlp = Mock()
        mock_nlp.pipe_names = []
        mock_doc = Mock()
        mock_doc.ents = []
        mock_nlp.pipe.return_value = [mock_doc]
        mock_spacy_load.return_value = mock_nlp

        recognizer = SpacyRecognizer()
        texts = ["Test text"]

        # Act
        recognizer.predict(texts)

        # Assert
        mock_nlp.pipe.assert_called_once_with(texts)

    @patch("geoparser.modules.recognizers.spacy.spacy.load")
    def test_extracts_entities_with_matching_types(self, mock_spacy_load):
        """Test that predict extracts only entities matching configured types."""
        # Arrange
        mock_nlp = Mock()
        mock_nlp.pipe_names = []

        # Create mock entities
        mock_entity_gpe = Mock()
        mock_entity_gpe.label_ = "GPE"
        mock_entity_gpe.start_char = 0
        mock_entity_gpe.end_char = 8

        mock_entity_person = Mock()
        mock_entity_person.label_ = "PERSON"
        mock_entity_person.start_char = 10
        mock_entity_person.end_char = 15

        mock_doc = Mock()
        mock_doc.ents = [mock_entity_gpe, mock_entity_person]
        mock_nlp.pipe.return_value = [mock_doc]
        mock_spacy_load.return_value = mock_nlp

        recognizer = SpacyRecognizer(entity_types=["GPE"])
        texts = ["New York and John"]

        # Act
        results = recognizer.predict(texts)

        # Assert
        assert len(results) == 1
        assert len(results[0]) == 1  # Only GPE entity
        assert results[0][0] == (0, 8)

    @patch("geoparser.modules.recognizers.spacy.spacy.load")
    def test_returns_empty_list_when_no_matching_entities(self, mock_spacy_load):
        """Test that predict returns empty list when no matching entities found."""
        # Arrange
        mock_nlp = Mock()
        mock_nlp.pipe_names = []

        mock_doc = Mock()
        mock_doc.ents = []
        mock_nlp.pipe.return_value = [mock_doc]
        mock_spacy_load.return_value = mock_nlp

        recognizer = SpacyRecognizer()
        texts = ["No entities here"]

        # Act
        results = recognizer.predict(texts)

        # Assert
        assert len(results) == 1
        assert results[0] == []

    @patch("geoparser.modules.recognizers.spacy.spacy.load")
    def test_processes_multiple_texts(self, mock_spacy_load):
        """Test that predict processes multiple texts correctly."""
        # Arrange
        mock_nlp = Mock()
        mock_nlp.pipe_names = []

        # Mock documents
        mock_doc1 = Mock()
        mock_entity1 = Mock()
        mock_entity1.label_ = "GPE"
        mock_entity1.start_char = 0
        mock_entity1.end_char = 5
        mock_doc1.ents = [mock_entity1]

        mock_doc2 = Mock()
        mock_entity2 = Mock()
        mock_entity2.label_ = "LOC"
        mock_entity2.start_char = 0
        mock_entity2.end_char = 4
        mock_doc2.ents = [mock_entity2]

        mock_nlp.pipe.return_value = [mock_doc1, mock_doc2]
        mock_spacy_load.return_value = mock_nlp

        recognizer = SpacyRecognizer(entity_types=["GPE", "LOC"])
        texts = ["Paris", "Rome"]

        # Act
        results = recognizer.predict(texts)

        # Assert
        assert len(results) == 2
        assert results[0] == [(0, 5)]
        assert results[1] == [(0, 4)]

    @patch("geoparser.modules.recognizers.spacy.spacy.load")
    def test_handles_empty_text_list(self, mock_spacy_load):
        """Test that predict handles empty text list."""
        # Arrange
        mock_nlp = Mock()
        mock_nlp.pipe_names = []
        mock_nlp.pipe.return_value = []
        mock_spacy_load.return_value = mock_nlp

        recognizer = SpacyRecognizer()
        texts = []

        # Act
        results = recognizer.predict(texts)

        # Assert
        assert results == []

    @patch("geoparser.modules.recognizers.spacy.spacy.load")
    def test_returns_character_offsets(self, mock_spacy_load):
        """Test that predict returns character offsets, not token offsets."""
        # Arrange
        mock_nlp = Mock()
        mock_nlp.pipe_names = []

        mock_entity = Mock()
        mock_entity.label_ = "GPE"
        mock_entity.start_char = 10  # Character offset
        mock_entity.end_char = 20

        mock_doc = Mock()
        mock_doc.ents = [mock_entity]
        mock_nlp.pipe.return_value = [mock_doc]
        mock_spacy_load.return_value = mock_nlp

        recognizer = SpacyRecognizer()
        texts = ["Some text New York here"]

        # Act
        results = recognizer.predict(texts)

        # Assert
        assert results[0][0] == (10, 20)  # Character offsets, not token positions


@pytest.mark.unit
class TestSpacyRecognizerGetDistilledLabel:
    """Test SpacyRecognizer _get_distilled_label method."""

    @patch("geoparser.modules.recognizers.spacy.spacy.load")
    def test_returns_entity_label_when_found_in_span(self, mock_spacy_load):
        """Test that _get_distilled_label returns entity label when found in span."""
        # Arrange
        mock_nlp = Mock()
        mock_nlp.pipe_names = []
        mock_spacy_load.return_value = mock_nlp

        recognizer = SpacyRecognizer(entity_types=["GPE", "LOC"])

        # Create mock base doc with char_span
        mock_entity = Mock()
        mock_entity.label_ = "GPE"

        mock_span = Mock()
        mock_span.ents = [mock_entity]

        mock_base_doc = Mock()
        mock_base_doc.char_span.return_value = mock_span

        # Act
        label = recognizer._get_distilled_label(0, 5, mock_base_doc)

        # Assert
        assert label == "GPE"
        mock_base_doc.char_span.assert_called_once_with(0, 5, alignment_mode="expand")

    @patch("geoparser.modules.recognizers.spacy.spacy.load")
    def test_returns_loc_as_fallback_when_no_entity_found(self, mock_spacy_load):
        """Test that _get_distilled_label returns LOC as fallback."""
        # Arrange
        mock_nlp = Mock()
        mock_nlp.pipe_names = []
        mock_spacy_load.return_value = mock_nlp

        recognizer = SpacyRecognizer()

        # Create mock base doc with no entities
        mock_span = Mock()
        mock_span.ents = []

        mock_token = Mock()
        mock_token.ent_type_ = ""
        mock_span.__iter__ = Mock(return_value=iter([mock_token]))

        mock_base_doc = Mock()
        mock_base_doc.char_span.return_value = mock_span

        # Act
        label = recognizer._get_distilled_label(0, 5, mock_base_doc)

        # Assert
        assert label == "LOC"

    @patch("geoparser.modules.recognizers.spacy.spacy.load")
    def test_returns_token_entity_type_when_found(self, mock_spacy_load):
        """Test that _get_distilled_label returns token entity type when no span entities."""
        # Arrange
        mock_nlp = Mock()
        mock_nlp.pipe_names = []
        mock_spacy_load.return_value = mock_nlp

        recognizer = SpacyRecognizer(entity_types=["GPE", "LOC"])

        # Create mock base doc with token entity
        mock_span = Mock()
        mock_span.ents = []

        mock_token = Mock()
        mock_token.ent_type_ = "LOC"
        mock_span.__iter__ = Mock(return_value=iter([mock_token]))

        mock_base_doc = Mock()
        mock_base_doc.char_span.return_value = mock_span

        # Act
        label = recognizer._get_distilled_label(0, 5, mock_base_doc)

        # Assert
        assert label == "LOC"

    @patch("geoparser.modules.recognizers.spacy.spacy.load")
    def test_returns_loc_when_char_span_is_none(self, mock_spacy_load):
        """Test that _get_distilled_label returns LOC when char_span returns None."""
        # Arrange
        mock_nlp = Mock()
        mock_nlp.pipe_names = []
        mock_spacy_load.return_value = mock_nlp

        recognizer = SpacyRecognizer()

        mock_base_doc = Mock()
        mock_base_doc.char_span.return_value = None

        # Act
        label = recognizer._get_distilled_label(0, 5, mock_base_doc)

        # Assert
        assert label == "LOC"


@pytest.mark.unit
class TestSpacyRecognizerPrepareTrainingData:
    """Test SpacyRecognizer _prepare_training_data method."""

    @patch("geoparser.modules.recognizers.spacy.spacy.load")
    def test_creates_training_examples_from_references(self, mock_spacy_load):
        """Test that _prepare_training_data creates training examples."""
        # Arrange
        mock_nlp = Mock()
        mock_nlp.pipe_names = []

        # Mock make_doc for creating training docs
        mock_doc = Mock()
        mock_nlp.make_doc.return_value = mock_doc

        mock_spacy_load.return_value = mock_nlp

        recognizer = SpacyRecognizer()

        # Mock the _load_spacy_model to return a base NLP
        mock_base_nlp = Mock()
        mock_base_doc = Mock()
        mock_base_nlp.return_value = mock_base_doc

        with patch.object(recognizer, "_load_spacy_model", return_value=mock_base_nlp):
            with patch.object(recognizer, "_get_distilled_label", return_value="GPE"):
                # Create mock Example.from_dict
                with patch(
                    "geoparser.modules.recognizers.spacy.Example"
                ) as mock_example:
                    mock_example_instance = Mock()
                    mock_example.from_dict.return_value = mock_example_instance

                    texts = ["Paris is beautiful"]
                    references = [[(0, 5)]]

                    # Act
                    examples = recognizer._prepare_training_data(texts, references)

                    # Assert
                    assert len(examples) == 1
                    assert examples[0] == mock_example_instance
                    mock_example.from_dict.assert_called_once()

    @patch("geoparser.modules.recognizers.spacy.spacy.load")
    def test_handles_multiple_references_in_document(self, mock_spacy_load):
        """Test that _prepare_training_data handles multiple references."""
        # Arrange
        mock_nlp = Mock()
        mock_nlp.pipe_names = []
        mock_doc = Mock()
        mock_nlp.make_doc.return_value = mock_doc
        mock_spacy_load.return_value = mock_nlp

        recognizer = SpacyRecognizer()

        mock_base_nlp = Mock()
        mock_base_doc = Mock()
        mock_base_nlp.return_value = mock_base_doc

        with patch.object(recognizer, "_load_spacy_model", return_value=mock_base_nlp):
            with patch.object(recognizer, "_get_distilled_label", return_value="GPE"):
                with patch(
                    "geoparser.modules.recognizers.spacy.Example"
                ) as mock_example:
                    mock_example_instance = Mock()
                    mock_example.from_dict.return_value = mock_example_instance

                    texts = ["Paris and London"]
                    references = [[(0, 5), (10, 16)]]

                    # Act
                    examples = recognizer._prepare_training_data(texts, references)

                    # Assert
                    assert len(examples) == 1
                    # Should have created one example with 2 entities
                    call_args = mock_example.from_dict.call_args[0]
                    entity_dict = call_args[1]
                    assert len(entity_dict["entities"]) == 2

    @patch("geoparser.modules.recognizers.spacy.spacy.load")
    def test_handles_multiple_documents(self, mock_spacy_load):
        """Test that _prepare_training_data handles multiple documents."""
        # Arrange
        mock_nlp = Mock()
        mock_nlp.pipe_names = []
        mock_doc = Mock()
        mock_nlp.make_doc.return_value = mock_doc
        mock_spacy_load.return_value = mock_nlp

        recognizer = SpacyRecognizer()

        mock_base_nlp = Mock()
        mock_base_doc = Mock()
        mock_base_nlp.return_value = mock_base_doc

        with patch.object(recognizer, "_load_spacy_model", return_value=mock_base_nlp):
            with patch.object(recognizer, "_get_distilled_label", return_value="GPE"):
                with patch(
                    "geoparser.modules.recognizers.spacy.Example"
                ) as mock_example:
                    mock_example_instance = Mock()
                    mock_example.from_dict.return_value = mock_example_instance

                    texts = ["Paris", "London"]
                    references = [[(0, 5)], [(0, 6)]]

                    # Act
                    examples = recognizer._prepare_training_data(texts, references)

                    # Assert
                    assert len(examples) == 2
