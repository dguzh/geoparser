"""
Tests for the training data SpacyRecognizer builds from annotations.

The existing tests mock spaCy heavily and only check how many examples come
back. These pin what actually flows through: which text each document is made
from, which spans get distilled, and the exact entity tuples handed to
``Example.from_dict``. Getting any of that wrong trains the model on the wrong
spans while still producing the right number of examples.
"""

from unittest.mock import Mock, patch

import pytest

from geoparser.modules.recognizers.spacy import SpacyRecognizer


@pytest.fixture
def recognizer():
    """A recognizer with spaCy stubbed out."""
    with patch("geoparser.modules.recognizers.spacy.spacy.load") as mock_load:
        nlp = Mock()
        nlp.pipe_names = []
        mock_load.return_value = nlp
        return SpacyRecognizer()


@pytest.fixture
def captured(recognizer):
    """
    Run _prepare_training_data over two documents, recording every call.

    Returns the recognizer plus the recorded make_doc texts, base-model texts,
    distillation arguments and Example.from_dict calls.
    """
    texts = ["Paris is lovely", "Berlin too"]
    references = [[(0, 5)], [(0, 6)]]

    made_docs = []
    recognizer.nlp.make_doc = Mock(
        side_effect=lambda text: made_docs.append(text) or f"doc:{text}"
    )

    base_texts = []
    base_nlp = Mock(side_effect=lambda text: base_texts.append(text) or f"base:{text}")

    distill_args = []

    def _distill(start, end, base_doc):
        distill_args.append((start, end, base_doc))
        return "GPE"

    with (
        patch.object(recognizer, "_load_spacy_model", return_value=base_nlp),
        patch.object(recognizer, "_get_distilled_label", side_effect=_distill),
        patch("geoparser.modules.recognizers.spacy.Example") as mock_example,
    ):
        mock_example.from_dict.side_effect = lambda doc, d: (doc, d)
        examples = recognizer._prepare_training_data(texts, references)

    return {
        "examples": examples,
        "made_docs": made_docs,
        "base_texts": base_texts,
        "distill_args": distill_args,
        "from_dict": mock_example.from_dict.call_args_list,
    }


@pytest.mark.unit
class TestPrepareTrainingData:
    """What the recognizer feeds spaCy for training."""

    def test_makes_one_doc_per_document_from_its_own_text(self, captured):
        """Each document is turned into a doc from that document's text."""
        assert captured["made_docs"] == ["Paris is lovely", "Berlin too"]

    def test_runs_the_base_model_over_each_document_text(self, captured):
        """Label distillation sees the same text, through the frozen pipeline."""
        assert captured["base_texts"] == ["Paris is lovely", "Berlin too"]

    def test_distills_each_reference_span_against_its_own_document(self, captured):
        """Offsets and the base doc are passed through in the right order."""
        assert captured["distill_args"] == [
            (0, 5, "base:Paris is lovely"),
            (0, 6, "base:Berlin too"),
        ]

    def test_builds_entity_tuples_of_start_end_and_label(self, captured):
        """The entity payload is (start, end, label) per reference."""
        payloads = [call.args[1] for call in captured["from_dict"]]
        assert payloads == [
            {"entities": [(0, 5, "GPE")]},
            {"entities": [(0, 6, "GPE")]},
        ]

    def test_pairs_each_entity_dict_with_its_own_doc(self, captured):
        """The doc handed to from_dict is the one made from the same text."""
        docs = [call.args[0] for call in captured["from_dict"]]
        assert docs == ["doc:Paris is lovely", "doc:Berlin too"]

    def test_returns_one_example_per_document(self, captured):
        """Every document yields exactly one training example."""
        assert len(captured["examples"]) == 2

    def test_rejects_mismatched_texts_and_references(self, recognizer):
        """
        A reference list that does not line up with the texts is an error.

        Zipping these without strict= would silently drop the extra document
        and train on less data than the caller supplied.
        """
        recognizer.nlp.make_doc = Mock(return_value="doc")
        with (
            patch.object(recognizer, "_load_spacy_model", return_value=Mock()),
            patch.object(recognizer, "_get_distilled_label", return_value="LOC"),
            patch("geoparser.modules.recognizers.spacy.Example"),
            pytest.raises(ValueError),
        ):
            recognizer._prepare_training_data(["a", "b"], [[(0, 1)]])

    def test_keeps_every_reference_of_a_multi_reference_document(self, recognizer):
        """All spans of one document end up in that document's entity list."""
        # Arrange
        recognizer.nlp.make_doc = Mock(return_value="doc")
        with (
            patch.object(recognizer, "_load_spacy_model", return_value=Mock()),
            patch.object(recognizer, "_get_distilled_label", return_value="LOC"),
            patch("geoparser.modules.recognizers.spacy.Example") as mock_example,
        ):
            # Act
            recognizer._prepare_training_data(
                ["Paris and Berlin"], [[(0, 5), (10, 16)]]
            )

            # Assert
            assert mock_example.from_dict.call_args.args[1] == {
                "entities": [(0, 5, "LOC"), (10, 16, "LOC")]
            }


@pytest.mark.unit
class TestLoadSpacyModel:
    """Loading the frozen base pipeline."""

    def test_downloads_then_reloads_the_named_model(self):
        """
        A missing model is downloaded and then loaded by name.

        The retry has to ask for the same model that failed; loading anything
        else would silently give the recognizer a different pipeline.
        """
        # Arrange
        with patch("geoparser.modules.recognizers.spacy.spacy") as mock_spacy:
            nlp = Mock()
            nlp.pipe_names = []
            mock_spacy.load.side_effect = [OSError("missing"), nlp, nlp]

            # Act
            recognizer = SpacyRecognizer(model_name="xx_test_model")

            # Assert
            mock_spacy.cli.download.assert_called_once_with("xx_test_model")
            assert mock_spacy.load.call_args_list[0].args == ("xx_test_model",)
            assert mock_spacy.load.call_args_list[1].args == ("xx_test_model",)
            assert recognizer.model_name == "xx_test_model"

    def test_removes_every_non_ner_component_that_is_present(self):
        """Only the four non-NER components are dropped, by exact name."""
        # Arrange
        with patch("geoparser.modules.recognizers.spacy.spacy.load") as mock_load:
            nlp = Mock()
            nlp.pipe_names = [
                "tagger",
                "parser",
                "attribute_ruler",
                "lemmatizer",
                "ner",
            ]
            mock_load.return_value = nlp

            # Act
            SpacyRecognizer()

            # Assert
            removed = [call.args[0] for call in nlp.remove_pipe.call_args_list]
            assert removed == ["tagger", "parser", "attribute_ruler", "lemmatizer"]

    def test_leaves_absent_components_alone(self):
        """A pipeline without those components has nothing removed."""
        # Arrange
        with patch("geoparser.modules.recognizers.spacy.spacy.load") as mock_load:
            nlp = Mock()
            nlp.pipe_names = ["ner"]
            mock_load.return_value = nlp

            # Act
            SpacyRecognizer()

            # Assert
            nlp.remove_pipe.assert_not_called()
