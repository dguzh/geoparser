"""
Unit tests for the GLiNER2 recognizer.

GLiNER2 is a zero-shot extractor: the entity types it looks for are given as
plain words at call time rather than baked into the model. That makes the
label list part of this module's configuration, and makes the mapping from
GLiNER2's per-label result dictionary back to flat character spans the part
worth pinning.
"""

from unittest.mock import Mock, patch

import pytest

from geoparser.modules.recognizers.gliner import GLiNER2Recognizer


@pytest.fixture
def extractor():
    """A patched AutoExtractor whose loaded model is a Mock."""
    with patch(
        "geoparser.modules.recognizers.gliner.AutoExtractor.from_pretrained"
    ) as from_pretrained:
        yield from_pretrained


def _entities(**by_label):
    """A GLiNER2 extraction result for one document."""
    return {"entities": dict(by_label)}


@pytest.mark.unit
class TestInitialization:
    """Loading the model and recording the configuration."""

    def test_defaults_to_the_multilingual_gliner_two_five_model(self, extractor):
        """The default checkpoint is the multilingual GLiNER2.5 release."""
        # Act
        recognizer = GLiNER2Recognizer()

        # Assert
        assert recognizer.model_name == "fastino/gliner2.5-multi-v1"
        extractor.assert_called_once_with("fastino/gliner2.5-multi-v1")

    def test_loads_the_model_that_was_asked_for(self, extractor):
        """A custom checkpoint is loaded instead of the default."""
        # Act
        GLiNER2Recognizer(model_name="fastino/other")

        # Assert
        extractor.assert_called_once_with("fastino/other")

    def test_defaults_to_the_three_geographic_labels(self, extractor):
        """Out of the box the recognizer looks for places, not people."""
        # Act
        recognizer = GLiNER2Recognizer()

        # Assert
        assert recognizer.entity_types == ["city", "country", "location"]

    def test_the_labels_are_part_of_the_module_identity(self, extractor):
        """
        Changing the label list changes the module id.

        Predictions are stored against the module id, so two recognizers
        looking for different things must not share one.
        """
        # Act
        default = GLiNER2Recognizer()
        narrowed = GLiNER2Recognizer(entity_types=["city"])

        # Assert
        assert narrowed.config["entity_types"] == ["city"]
        assert narrowed.id != default.id

    def test_the_default_label_list_cannot_be_mutated_by_a_caller(self, extractor):
        """Each recognizer gets its own copy of the default labels."""
        # Arrange
        first = GLiNER2Recognizer()

        # Act
        first.entity_types.append("person")

        # Assert
        assert GLiNER2Recognizer().entity_types == ["city", "country", "location"]

    def test_rejects_an_empty_label_list(self, extractor):
        """A zero-shot extractor with no labels can never find anything."""
        # Act & Assert
        with pytest.raises(ValueError, match="at least one entity type"):
            GLiNER2Recognizer(entity_types=[])


@pytest.mark.unit
class TestPredict:
    """Turning GLiNER2 output into reference spans."""

    @staticmethod
    def _recognizer(extractor, results, **kwargs):
        """A recognizer whose model returns `results`, one per document."""
        model = Mock()
        model.extract_entities = Mock(side_effect=list(results))
        extractor.return_value = model
        recognizer = GLiNER2Recognizer(**kwargs)
        return recognizer, model

    def test_asks_for_spans_of_the_configured_labels(self, extractor):
        """Every call names the label list and requests character offsets."""
        # Arrange
        recognizer, model = self._recognizer(
            extractor, [_entities()], entity_types=["city"]
        )

        # Act
        recognizer.predict(["Paris"])

        # Assert
        model.extract_entities.assert_called_once_with(
            "Paris", ["city"], include_spans=True
        )

    def test_returns_one_span_list_per_document_in_order(self, extractor):
        """The result mirrors the input, document for document."""
        # Arrange
        recognizer, _ = self._recognizer(
            extractor,
            [
                _entities(city=[{"text": "Paris", "start": 0, "end": 5}]),
                _entities(country=[{"text": "Peru", "start": 3, "end": 7}]),
            ],
        )

        # Act
        references = recognizer.predict(["Paris is nice", "In Peru"])

        # Assert
        assert references == [[(0, 5)], [(3, 7)]]

    def test_merges_the_labels_into_one_ordered_span_list(self, extractor):
        """
        Spans from every label are returned together, in document order.

        GLiNER2 groups its results by label, so the natural iteration order is
        by label and then by position. Leaving the spans in that order would
        hand the resolver a reference list that does not follow the text.
        """
        # Arrange
        recognizer, _ = self._recognizer(
            extractor,
            [
                _entities(
                    country=[{"text": "France", "start": 10, "end": 16}],
                    city=[{"text": "Paris", "start": 0, "end": 5}],
                )
            ],
        )

        # Act
        references = recognizer.predict(["Paris, in France"])

        # Assert
        assert references == [[(0, 5), (10, 16)]]

    def test_drops_duplicate_spans_found_under_several_labels(self, extractor):
        """A span matching two labels is one reference, not two."""
        # Arrange
        recognizer, _ = self._recognizer(
            extractor,
            [
                _entities(
                    city=[{"text": "Monaco", "start": 0, "end": 6}],
                    country=[{"text": "Monaco", "start": 0, "end": 6}],
                )
            ],
        )

        # Act
        references = recognizer.predict(["Monaco"])

        # Assert
        assert references == [[(0, 6)]]

    def test_a_document_with_no_entities_yields_an_empty_list(self, extractor):
        """Finding nothing is an empty list, not None."""
        # Arrange
        recognizer, _ = self._recognizer(extractor, [_entities()])

        # Act & Assert
        assert recognizer.predict(["nothing here"]) == [[]]

    def test_no_documents_means_no_calls_and_no_results(self, extractor):
        """An empty batch does not touch the model."""
        # Arrange
        recognizer, model = self._recognizer(extractor, [])

        # Act
        references = recognizer.predict([])

        # Assert
        assert references == []
        model.extract_entities.assert_not_called()

    def test_ignores_an_entity_without_offsets(self, extractor):
        """
        An entity the model could not locate is skipped.

        Every reference is stored as a span into the document text, so an
        entity with no offsets has nowhere to go; keeping it would mean
        inventing a position.
        """
        # Arrange
        recognizer, _ = self._recognizer(
            extractor,
            [
                _entities(
                    city=[
                        {"text": "Paris", "start": 0, "end": 5},
                        {"text": "Nowhere"},
                    ]
                )
            ],
        )

        # Act
        references = recognizer.predict(["Paris"])

        # Assert
        assert references == [[(0, 5)]]

    def test_a_result_without_an_entities_key_is_treated_as_empty(self, extractor):
        """A model that returns nothing usable yields no references."""
        # Arrange
        recognizer, _ = self._recognizer(extractor, [{}])

        # Act & Assert
        assert recognizer.predict(["text"]) == [[]]


@pytest.mark.unit
class TestModelNameIdentity:
    """The checkpoint is part of what identifies the recognizer."""

    def test_the_checkpoint_reaches_the_recorded_config(self, extractor):
        """The model name is stored, not only used to load."""
        # Act
        recognizer = GLiNER2Recognizer(model_name="fastino/other")

        # Assert
        assert recognizer.config["model_name"] == "fastino/other"

    def test_two_checkpoints_get_two_module_ids(self, extractor):
        """
        Predictions from different checkpoints are kept apart.

        Two recognizers looking for the same labels with different models
        produce different annotations, so sharing an id would conflate them.
        """
        # Act
        default = GLiNER2Recognizer()
        other = GLiNER2Recognizer(model_name="fastino/other")

        # Assert
        assert other.id != default.id


@pytest.mark.unit
class TestPartialOffsets:
    """Entities the model located only halfway."""

    def test_an_entity_with_only_a_start_is_skipped(self, extractor):
        """
        Both ends are needed, not either one.

        A half-located entity cannot be turned into a span, and taking it
        anyway would raise deep inside the caller rather than here.
        """
        # Arrange
        model = Mock()
        model.extract_entities = Mock(
            return_value={
                "entities": {
                    "city": [
                        {"text": "Paris", "start": 0},
                        {"text": "Berlin", "start": 10, "end": 16},
                    ]
                }
            }
        )
        extractor.return_value = model
        recognizer = GLiNER2Recognizer()

        # Act & Assert
        assert recognizer.predict(["x"]) == [[(10, 16)]]

    def test_an_entity_with_only_an_end_is_skipped(self, extractor):
        """The same holds for the other end."""
        # Arrange
        model = Mock()
        model.extract_entities = Mock(
            return_value={"entities": {"city": [{"text": "Paris", "end": 5}]}}
        )
        extractor.return_value = model
        recognizer = GLiNER2Recognizer()

        # Act & Assert
        assert recognizer.predict(["x"]) == [[]]
