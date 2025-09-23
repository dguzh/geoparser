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


@pytest.fixture
def mock_documents_with_references():
    """Create mock Document objects with reference annotations for training."""
    doc1 = MagicMock()
    doc1.text = "I visited London and Paris last year."
    doc1.references = [
        MagicMock(start=10, end=16),  # "London"
        MagicMock(start=21, end=26),  # "Paris"
    ]

    doc2 = MagicMock()
    doc2.text = "New York is a great city."
    doc2.references = [
        MagicMock(start=0, end=8),  # "New York"
    ]

    return [doc1, doc2]


@pytest.fixture
def mock_spacy_doc_with_entities():
    """Create a mock spaCy Doc with entities for testing label distillation."""
    # Mock entities
    ent1 = MagicMock()
    ent1.start_char = 10
    ent1.end_char = 16
    ent1.label_ = "GPE"

    ent2 = MagicMock()
    ent2.start_char = 21
    ent2.end_char = 26
    ent2.label_ = "GPE"

    # Mock tokens
    token1 = MagicMock()
    token1.ent_type_ = "GPE"

    token2 = MagicMock()
    token2.ent_type_ = "LOC"

    # Mock span
    mock_span = MagicMock()
    mock_span.ents = [ent1, ent2]
    mock_span.__iter__ = lambda self: iter([token1, token2])

    # Mock doc
    mock_doc = MagicMock()
    mock_doc.char_span.return_value = mock_span

    return mock_doc


def test_get_distilled_label_exact_entity_match():
    """Test _get_distilled_label when span exactly matches an entity."""
    with patch("geoparser.modules.recognizers.spacy.spacy.load") as mock_load:
        with patch.object(SpacyRecognizer, "_load", return_value="mock-id"):
            mock_nlp = MagicMock()
            mock_load.return_value = mock_nlp

            recognizer = SpacyRecognizer()

            # Mock entity that matches exactly
            mock_entity = MagicMock()
            mock_entity.label_ = "GPE"

            mock_span = MagicMock()
            mock_span.ents = [mock_entity]

            mock_doc = MagicMock()
            mock_doc.char_span.return_value = mock_span

            result = recognizer._get_distilled_label(10, 16, mock_doc)

            assert result == "GPE"
            mock_doc.char_span.assert_called_once_with(10, 16, alignment_mode="expand")


def test_get_distilled_label_token_level_match():
    """Test _get_distilled_label when no exact entity match but token has entity type."""
    with patch("geoparser.modules.recognizers.spacy.spacy.load") as mock_load:
        with patch.object(SpacyRecognizer, "_load", return_value="mock-id"):
            mock_nlp = MagicMock()
            mock_load.return_value = mock_nlp

            recognizer = SpacyRecognizer()

            # Mock token with entity type
            mock_token = MagicMock()
            mock_token.ent_type_ = "LOC"

            mock_span = MagicMock()
            mock_span.ents = []  # No exact entity match
            mock_span.__iter__ = lambda self: iter([mock_token])

            mock_doc = MagicMock()
            mock_doc.char_span.return_value = mock_span

            result = recognizer._get_distilled_label(10, 16, mock_doc)

            assert result == "LOC"


def test_get_distilled_label_no_match_fallback():
    """Test _get_distilled_label fallback to 'LOC' when no match found."""
    with patch("geoparser.modules.recognizers.spacy.spacy.load") as mock_load:
        with patch.object(SpacyRecognizer, "_load", return_value="mock-id"):
            mock_nlp = MagicMock()
            mock_load.return_value = mock_nlp

            recognizer = SpacyRecognizer()

            mock_doc = MagicMock()
            mock_doc.char_span.return_value = None  # No span found

            result = recognizer._get_distilled_label(10, 16, mock_doc)

            assert result == "LOC"


def test_get_distilled_label_filtered_entity_types():
    """Test _get_distilled_label respects entity_types filter."""
    with patch("geoparser.modules.recognizers.spacy.spacy.load") as mock_load:
        with patch.object(SpacyRecognizer, "_load", return_value="mock-id"):
            mock_nlp = MagicMock()
            mock_load.return_value = mock_nlp

            # Only GPE and LOC are valid
            recognizer = SpacyRecognizer(entity_types={"GPE", "LOC"})

            # Mock entity with PERSON type (should be filtered)
            mock_entity = MagicMock()
            mock_entity.label_ = "PERSON"

            # Mock token with LOC type (should match)
            mock_token = MagicMock()
            mock_token.ent_type_ = "LOC"

            mock_span = MagicMock()
            mock_span.ents = [mock_entity]  # PERSON entity should be ignored
            mock_span.__iter__ = lambda self: iter([mock_token])

            mock_doc = MagicMock()
            mock_doc.char_span.return_value = mock_span

            result = recognizer._get_distilled_label(10, 16, mock_doc)

            assert result == "LOC"  # Should find LOC from token, not PERSON from entity


def test_prepare_training_data_with_distillation(mock_documents_with_references):
    """Test _prepare_training_data uses label distillation correctly."""
    with patch("geoparser.modules.recognizers.spacy.spacy.load") as mock_load:
        with patch.object(SpacyRecognizer, "_load", return_value="mock-id"):
            # Mock the main nlp pipeline
            mock_nlp = MagicMock()
            mock_doc1 = MagicMock()
            mock_doc2 = MagicMock()
            mock_nlp.make_doc.side_effect = [mock_doc1, mock_doc2]

            # Mock the base nlp pipeline for distillation
            mock_base_nlp = MagicMock()
            mock_base_doc1 = MagicMock()
            mock_base_doc2 = MagicMock()

            mock_load.side_effect = [
                mock_nlp,
                mock_base_nlp,
            ]  # First call for init, second for distillation

            recognizer = SpacyRecognizer()

            # Mock _get_distilled_label calls
            with patch.object(recognizer, "_get_distilled_label") as mock_distill:
                mock_distill.side_effect = [
                    "GPE",
                    "GPE",
                    "LOC",
                ]  # Labels for the 3 references

                # Mock base_nlp calls
                mock_base_nlp.side_effect = [mock_base_doc1, mock_base_doc2]

                # Mock Example.from_dict at module level
                with patch(
                    "geoparser.modules.recognizers.spacy.Example"
                ) as mock_example_class:
                    mock_example1 = MagicMock()
                    mock_example2 = MagicMock()
                    mock_example_class.from_dict.side_effect = [
                        mock_example1,
                        mock_example2,
                    ]

                    result = recognizer._prepare_training_data(
                        mock_documents_with_references
                    )

                    # Verify distillation was called for each reference
                    assert mock_distill.call_count == 3
                    mock_distill.assert_any_call(10, 16, mock_base_doc1)  # London
                    mock_distill.assert_any_call(21, 26, mock_base_doc1)  # Paris
                    mock_distill.assert_any_call(0, 8, mock_base_doc2)  # New York

                    # Verify Example creation with distilled labels
                    expected_entities1 = [(10, 16, "GPE"), (21, 26, "GPE")]
                    expected_entities2 = [(0, 8, "LOC")]

                    mock_example_class.from_dict.assert_any_call(
                        mock_doc1, {"entities": expected_entities1}
                    )
                    mock_example_class.from_dict.assert_any_call(
                        mock_doc2, {"entities": expected_entities2}
                    )

                    assert result == [mock_example1, mock_example2]


def test_fit_method_complete_workflow(mock_documents_with_references, tmp_path):
    """Test the complete fit method workflow with training."""
    with patch("geoparser.modules.recognizers.spacy.spacy.load") as mock_load:
        with patch.object(SpacyRecognizer, "_load", return_value="mock-id"):
            mock_nlp = MagicMock()
            mock_load.return_value = mock_nlp

            # Mock optimizer
            mock_optimizer = MagicMock()
            mock_nlp.resume_training.return_value = mock_optimizer

            recognizer = SpacyRecognizer()

            # Mock training data preparation
            mock_examples = [MagicMock(), MagicMock()]
            with patch.object(recognizer, "_prepare_training_data") as mock_prepare:
                mock_prepare.return_value = mock_examples

                # Mock Path.mkdir and nlp.to_disk
                with patch(
                    "geoparser.modules.recognizers.spacy.Path"
                ) as mock_path_class:
                    mock_path = MagicMock()
                    mock_path_class.return_value = mock_path

                    output_path = str(tmp_path / "test_model")

                    recognizer.fit(
                        documents=mock_documents_with_references,
                        output_path=output_path,
                        epochs=2,
                        batch_size=4,
                        dropout=0.2,
                        learning_rate=0.002,
                    )

                    # Verify training data preparation
                    mock_prepare.assert_called_once_with(mock_documents_with_references)

                    # Verify optimizer setup
                    mock_nlp.resume_training.assert_called_once()
                    assert mock_optimizer.learn_rate == 0.002

                    # Verify training loop (2 epochs)
                    assert mock_nlp.update.call_count == 2  # 2 batches per epoch

                    # Verify model saving
                    mock_path_class.assert_called_once_with(output_path)
                    mock_path.mkdir.assert_called_once_with(parents=True, exist_ok=True)
                    mock_nlp.to_disk.assert_called_once_with(output_path)


def test_fit_method_no_training_examples():
    """Test fit method raises error when no training examples are created."""
    with patch("geoparser.modules.recognizers.spacy.spacy.load") as mock_load:
        with patch.object(SpacyRecognizer, "_load", return_value="mock-id"):
            mock_nlp = MagicMock()
            mock_load.return_value = mock_nlp

            recognizer = SpacyRecognizer()

            # Mock empty training data
            with patch.object(recognizer, "_prepare_training_data") as mock_prepare:
                mock_prepare.return_value = []

                with pytest.raises(ValueError, match="No training examples found"):
                    recognizer.fit(documents=[], output_path="/tmp/test")


def test_fit_method_default_parameters(mock_documents_with_references, tmp_path):
    """Test fit method with default parameters."""
    with patch("geoparser.modules.recognizers.spacy.spacy.load") as mock_load:
        with patch.object(SpacyRecognizer, "_load", return_value="mock-id"):
            mock_nlp = MagicMock()
            mock_load.return_value = mock_nlp

            mock_optimizer = MagicMock()
            mock_nlp.resume_training.return_value = mock_optimizer

            recognizer = SpacyRecognizer()

            mock_examples = [MagicMock()]
            with patch.object(recognizer, "_prepare_training_data") as mock_prepare:
                mock_prepare.return_value = mock_examples

                with patch("geoparser.modules.recognizers.spacy.Path"):
                    output_path = str(tmp_path / "test_model")

                    recognizer.fit(
                        documents=mock_documents_with_references,
                        output_path=output_path,
                    )

                    # Verify default parameters were used
                    assert mock_optimizer.learn_rate == 0.001  # default learning_rate

                    # Verify 10 epochs (default) with 1 example means 10 update calls
                    assert mock_nlp.update.call_count == 10
