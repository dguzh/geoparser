"""
Zero-shot toponym recognition with GLiNER2.

GLiNER2 is given the entity types to look for as ordinary words at call time,
so this module needs no fine-tuning to recognize place names, and the label
list is a configuration choice rather than a property of the checkpoint.
"""

import typing as t

from gliner2 import AutoExtractor

from geoparser.modules.recognizers import Recognizer


class GLiNER2Recognizer(Recognizer):
    """
    A recognition module that uses GLiNER2 to identify references in text.

    The model is asked for the configured entity types and returns the spans
    it found for each of them; those spans are flattened into one list of
    (start, end) offsets per document, in the order they appear in the text.
    """

    NAME = "GLiNER2Recognizer"

    # The multilingual GLiNER2.5 release: one checkpoint for every language
    # the corpus might be in, which a per-language NER model cannot offer.
    DEFAULT_MODEL_NAME = "fastino/gliner2.5-multi-v1"

    # A tuple, so the class-level default cannot be mutated through an
    # instance. Module.__init__ normalizes it to a list via its JSON round
    # trip, which is also what makes the recorded config comparable.
    DEFAULT_ENTITY_TYPES: t.ClassVar[tuple[str, ...]] = (
        "city",
        "country",
        "location",
    )

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL_NAME,
        entity_types: t.Sequence[str] = DEFAULT_ENTITY_TYPES,
    ):
        """
        Initialize the GLiNER2 recognition module.

        Args:
            model_name: HuggingFace checkpoint to extract with
            entity_types: Entity types to ask the model for. These are plain
                          words, not a fixed label set: the model matches them
                          zero-shot.

        Raises:
            ValueError: If no entity types are given, since a zero-shot
                extractor with nothing to look for can never find anything
        """
        entity_types = list(entity_types)
        if not entity_types:
            # pragma: no mutate start - wording only; a test pins the type and
            # that the message names what is missing.
            raise ValueError(
                "GLiNER2Recognizer needs at least one entity type to look for."
            )
            # pragma: no mutate end

        super().__init__(model_name=model_name, entity_types=entity_types)

        self.model_name = model_name
        self.entity_types = entity_types
        self.model = AutoExtractor.from_pretrained(model_name)

    def predict(self, texts: list[str]) -> list[list[tuple[int, int]] | None]:
        """
        Identify references in multiple document texts.

        Args:
            texts: List of document text strings to process

        Returns:
            One list of (start, end) offsets per input document, in the same
            order as the texts, each ordered by position in its document.
        """
        return [self._document_references(text) for text in texts]

    def _document_references(self, text: str) -> list[tuple[int, int]]:
        """
        The reference spans GLiNER2 finds in one document.

        Args:
            text: The document text

        Returns:
            The distinct spans, ordered by position in the text
        """
        result = self.model.extract_entities(
            text, self.entity_types, include_spans=True
        )
        return sorted(self._spans(result.get("entities", {})))

    @staticmethod
    def _spans(by_label: dict[str, list[dict]]) -> set[tuple[int, int]]:
        """
        The distinct character spans across every label GLiNER2 reported.

        A span found under two labels is one reference, and an entity the
        model could not locate in the text is skipped: a reference is stored
        as a span, so one without offsets has nowhere to go.

        Args:
            by_label: GLiNER2's entities, grouped by the label they matched

        Returns:
            The set of (start, end) offsets
        """
        return {
            (entity["start"], entity["end"])
            for entities in by_label.values()
            for entity in entities
            if "start" in entity and "end" in entity
        }
