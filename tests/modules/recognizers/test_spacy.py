from unittest.mock import MagicMock, patch

import pytest

from geoparser.modules.recognizers.spacy import SpacyRecognizer


@pytest.fixture
def mock_spacy_model():
    """Create a mock spaCy model."""
    mock_nlp = MagicMock()
    mock_nlp.pipe_names = [
        "tok2vec",
        "tagger",
        "parser",
        "ner",
        "attribute_ruler",
        "lemmatizer",
    ]
    mock_nlp.disable_pipes = MagicMock()
    return mock_nlp


@pytest.fixture
def mock_documents():
    """Create mock Document objects for testing."""
    doc1 = MagicMock()
    doc1.text = "I visited London and Paris last year."

    doc2 = MagicMock()
    doc2.text = "New York is a great city with many facilities."

    return [doc1, doc2]


def test_spacy_recognizer_initialization_default():
    """Test SpacyRecognizer initialization with default parameters."""
    with patch("geoparser.modules.recognizers.spacy.spacy.load") as mock_load:
        with patch.object(SpacyRecognizer, "_load", return_value="mock-id"):
            mock_load.return_value = MagicMock()

            recognizer = SpacyRecognizer()

            assert recognizer.name == "SpacyRecognizer"
            assert recognizer.model_name == "en_core_web_sm"
            assert recognizer.entity_types == {"GPE", "LOC", "FAC"}
            mock_load.assert_called_once_with("en_core_web_sm")


def test_spacy_recognizer_initialization_custom():
    """Test SpacyRecognizer initialization with custom parameters."""
    with patch("geoparser.modules.recognizers.spacy.spacy.load") as mock_load:
        with patch.object(SpacyRecognizer, "_load", return_value="mock-id"):
            mock_load.return_value = MagicMock()

            custom_entity_types = {"GPE", "LOC"}
            recognizer = SpacyRecognizer(
                model_name="en_core_web_lg", entity_types=custom_entity_types
            )

            assert recognizer.model_name == "en_core_web_lg"
            assert recognizer.entity_types == custom_entity_types
            mock_load.assert_called_once_with("en_core_web_lg")


def test_load_spacy_model(mock_spacy_model):
    """Test _load_spacy_model method disables unnecessary components."""
    with patch(
        "geoparser.modules.recognizers.spacy.spacy.load", return_value=mock_spacy_model
    ):
        with patch.object(SpacyRecognizer, "_load", return_value="mock-id"):
            recognizer = SpacyRecognizer()

            # Verify disable_pipes was called with the correct components
            expected_components = [
                "tok2vec",
                "tagger",
                "parser",
                "attribute_ruler",
                "lemmatizer",
            ]
            mock_spacy_model.disable_pipes.assert_called_once_with(*expected_components)


def test_load_spacy_model_partial_components(mock_spacy_model):
    """Test _load_spacy_model when some components don't exist."""
    # Simulate a model that doesn't have all components
    mock_spacy_model.pipe_names = ["tagger", "ner"]  # Only has tagger and ner

    with patch(
        "geoparser.modules.recognizers.spacy.spacy.load", return_value=mock_spacy_model
    ):
        with patch.object(SpacyRecognizer, "_load", return_value="mock-id"):
            recognizer = SpacyRecognizer()

            # Should only try to disable the component that exists
            mock_spacy_model.disable_pipes.assert_called_once_with("tagger")


def test_predict_references_single_document():
    """Test predict_references with a single document."""
    # Mock spaCy entities
    mock_ent1 = MagicMock()
    mock_ent1.start_char = 10
    mock_ent1.end_char = 16
    mock_ent1.label_ = "GPE"

    mock_ent2 = MagicMock()
    mock_ent2.start_char = 21
    mock_ent2.end_char = 26
    mock_ent2.label_ = "GPE"

    # Mock processed document
    mock_doc = MagicMock()
    mock_doc.ents = [mock_ent1, mock_ent2]

    # Mock nlp.pipe to return the processed document
    mock_nlp = MagicMock()
    mock_nlp.pipe.return_value = [mock_doc]

    with patch("geoparser.modules.recognizers.spacy.spacy.load", return_value=mock_nlp):
        with patch.object(SpacyRecognizer, "_load", return_value="mock-id"):
            recognizer = SpacyRecognizer()

            # Create mock document
            mock_document = MagicMock()
            mock_document.text = "I visited London and Paris last year."

            result = recognizer.predict_references([mock_document])

            # Verify the result
            assert len(result) == 1
            assert result[0] == [(10, 16), (21, 26)]

            # Verify nlp.pipe was called with the document text
            mock_nlp.pipe.assert_called_once_with(
                ["I visited London and Paris last year."]
            )


def test_predict_references_multiple_documents(mock_documents):
    """Test predict_references with multiple documents."""
    # Mock spaCy entities for first document
    mock_ent1 = MagicMock()
    mock_ent1.start_char = 10
    mock_ent1.end_char = 16
    mock_ent1.label_ = "GPE"

    # Mock spaCy entities for second document
    mock_ent2 = MagicMock()
    mock_ent2.start_char = 0
    mock_ent2.end_char = 8
    mock_ent2.label_ = "GPE"

    mock_ent3 = MagicMock()
    mock_ent3.start_char = 35
    mock_ent3.end_char = 45
    mock_ent3.label_ = "FAC"

    # Mock processed documents
    mock_doc1 = MagicMock()
    mock_doc1.ents = [mock_ent1]

    mock_doc2 = MagicMock()
    mock_doc2.ents = [mock_ent2, mock_ent3]

    # Mock nlp.pipe to return the processed documents
    mock_nlp = MagicMock()
    mock_nlp.pipe.return_value = [mock_doc1, mock_doc2]

    with patch("geoparser.modules.recognizers.spacy.spacy.load", return_value=mock_nlp):
        with patch.object(SpacyRecognizer, "_load", return_value="mock-id"):
            recognizer = SpacyRecognizer()

            result = recognizer.predict_references(mock_documents)

            # Verify the result
            assert len(result) == 2
            assert result[0] == [(10, 16)]
            assert result[1] == [(0, 8), (35, 45)]


def test_predict_references_filtered_entity_types():
    """Test that only specified entity types are included."""
    # Mock entities with different types
    mock_ent1 = MagicMock()
    mock_ent1.start_char = 0
    mock_ent1.end_char = 6
    mock_ent1.label_ = "GPE"  # Should be included

    mock_ent2 = MagicMock()
    mock_ent2.start_char = 10
    mock_ent2.end_char = 15
    mock_ent2.label_ = "PERSON"  # Should be filtered out

    mock_ent3 = MagicMock()
    mock_ent3.start_char = 20
    mock_ent3.end_char = 23
    mock_ent3.label_ = "LOC"  # Should be included

    # Mock processed document
    mock_doc = MagicMock()
    mock_doc.ents = [mock_ent1, mock_ent2, mock_ent3]

    # Mock nlp.pipe
    mock_nlp = MagicMock()
    mock_nlp.pipe.return_value = [mock_doc]

    with patch("geoparser.modules.recognizers.spacy.spacy.load", return_value=mock_nlp):
        with patch.object(SpacyRecognizer, "_load", return_value="mock-id"):
            # Initialize with only GPE and LOC
            recognizer = SpacyRecognizer(entity_types={"GPE", "LOC"})

            mock_document = MagicMock()
            mock_document.text = "Test text"

            result = recognizer.predict_references([mock_document])

            # Should only include GPE and LOC entities
            assert len(result) == 1
            assert result[0] == [(0, 6), (20, 23)]


def test_predict_references_empty_documents():
    """Test predict_references with empty document list."""
    with patch("geoparser.modules.recognizers.spacy.spacy.load") as mock_load:
        with patch.object(SpacyRecognizer, "_load", return_value="mock-id"):
            mock_nlp = MagicMock()
            mock_load.return_value = mock_nlp

            recognizer = SpacyRecognizer()
            result = recognizer.predict_references([])

            assert result == []
            mock_nlp.pipe.assert_called_once_with([])


def test_predict_references_no_entities():
    """Test predict_references when no entities are found."""
    # Mock processed document with no entities
    mock_doc = MagicMock()
    mock_doc.ents = []

    # Mock nlp.pipe
    mock_nlp = MagicMock()
    mock_nlp.pipe.return_value = [mock_doc]

    with patch("geoparser.modules.recognizers.spacy.spacy.load", return_value=mock_nlp):
        with patch.object(SpacyRecognizer, "_load", return_value="mock-id"):
            recognizer = SpacyRecognizer()

            mock_document = MagicMock()
            mock_document.text = "This text has no location entities."

            result = recognizer.predict_references([mock_document])

            assert len(result) == 1
            assert result[0] == []


def test_spacy_recognizer_config():
    """Test that SpacyRecognizer correctly stores configuration."""
    with patch("geoparser.modules.recognizers.spacy.spacy.load") as mock_load:
        with patch.object(SpacyRecognizer, "_load", return_value="mock-id"):
            mock_load.return_value = MagicMock()

            recognizer = SpacyRecognizer(
                model_name="en_core_web_md", entity_types={"GPE", "LOC"}
            )

            # Check that config is properly stored (sets are normalized to lists)
            expected_config = {
                "entity_types": ["GPE", "LOC"],  # Set becomes sorted list
                "model_name": "en_core_web_md",
            }
            assert recognizer.config == expected_config
