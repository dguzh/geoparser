import random
import typing as t
from pathlib import Path

import spacy
import spacy.tokens
from spacy.training import Example

from geoparser.modules.recognizers import Recognizer


class SpacyRecognizer(Recognizer):
    """
    A recognition module that uses spaCy to identify references in document text.

    This module identifies location-based named entities like GPE (geopolitical entity),
    LOC (location), and FAC (facility) as potential references.
    """

    NAME = "SpacyRecognizer"

    # A tuple, so the default cannot be mutated by a caller. It is normalized
    # to a list by the JSON round-trip in Module.__init__, which keeps the
    # recorded config -- and therefore the module id -- byte-for-byte the same
    # as when this default was a list literal.
    DEFAULT_ENTITY_TYPES: t.ClassVar[tuple[str, ...]] = ("FAC", "GPE", "LOC")

    def __init__(
        self,
        model_name: str = "en_core_web_sm",
        entity_types: t.Sequence[str] = DEFAULT_ENTITY_TYPES,
    ):
        """
        Initialize the SpaCy recognition module.

        Args:
            model_name: spaCy model to use (default: "en_core_web_sm")
            entity_types: List of spaCy entity types to consider as references
                          (default: ["FAC", "GPE", "LOC"])
        """
        # Initialize parent with the parameters
        super().__init__(model_name=model_name, entity_types=entity_types)

        # Store instance attributes directly from parameters
        self.model_name = model_name
        # Convert entity_types to set for efficient lookups
        self.entity_types = set(entity_types)

        # Load spaCy model with optimized pipeline
        self.nlp = self._load_spacy_model()

    def _load_spacy_model(self) -> spacy.language.Language:
        """
        Load and configure the spaCy model with optimized pipeline.

        Loads the specified model and removes unnecessary pipeline components
        to optimize performance for NER tasks. If the model is not available,
        it will be automatically downloaded.

        Returns:
            Configured spaCy Language model
        """
        # Try to load spaCy model, download if not available
        try:
            nlp = spacy.load(self.model_name)
        except OSError:
            # Model not found, download it
            # Progress text, not behaviour; the download and reload below are
            # what the tests pin.
            print(
                f"Downloading spaCy model '{self.model_name}'..."
            )  # pragma: no mutate
            spacy.cli.download(self.model_name)
            nlp = spacy.load(self.model_name)

        # Remove non-NER components to optimize performance
        pipe_components = [
            "tagger",
            "parser",
            "attribute_ruler",
            "lemmatizer",
        ]
        for pipe_name in [p for p in pipe_components if p in nlp.pipe_names]:
            nlp.remove_pipe(pipe_name)
        return nlp

    def predict(self, texts: list[str]) -> list[list[tuple[int, int]] | None]:
        """
        Identify references (location entities) in multiple document texts using spaCy.

        Args:
            texts: List of document text strings to process

        Returns:
            A list where each element corresponds to one document at the same index in the
            input list. Each element is either a list of (start, end) tuples containing
            positions of references found in the document, or None if predictions are not
            available for that document.
        """
        results = []

        # Process documents in batches using spaCy's nlp.pipe for efficiency
        docs = list(self.nlp.pipe(texts))

        # Extract reference offsets for each document
        for doc in docs:
            # Find all entities that match our entity types of interest
            references = [
                (ent.start_char, ent.end_char)
                for ent in doc.ents
                if ent.label_ in self.entity_types
            ]
            results.append(references)

        return results

    def fit(
        self,
        texts: list[str],
        references: list[list[tuple[int, int]]],
        output_path: str | Path,
        epochs: int = 10,
        batch_size: int = 8,
        dropout: float = 0.1,
        learning_rate: float = 0.001,
    ) -> None:
        """
        Fine-tune the spaCy NER model using documents with reference annotations.
        This method gathers all references from the provided documents and uses them
        to create training examples for fine-tuning the underlying spaCy NER model.

        Args:
            texts: List of document text strings
            references: List of lists of (start, end) position tuples
            output_path: Directory path to save the fine-tuned model
            epochs: Number of training epochs (default: 10)
            batch_size: Training batch size (default: 8)
            dropout: Dropout rate for training (default: 0.1)
            learning_rate: Learning rate for training (default: 0.001)

        Raises:
            ValueError: If no training examples can be created from the provided documents
        """
        print("Preparing training data from reference annotations...")

        # Prepare training data
        examples = self._prepare_training_data(texts, references)

        if not examples:
            raise ValueError(
                "No training examples found. Ensure documents contain reference annotations."
            )

        print(f"Created {len(examples)} training examples")

        # Initialize optimizer
        optimizer = self.nlp.resume_training()
        optimizer.learn_rate = learning_rate

        print("Starting model fine-tuning...")

        # Training loop
        losses = {}
        for _epoch in range(epochs):
            # Shuffle examples for each epoch
            epoch_examples = examples.copy()
            random.shuffle(epoch_examples)

            # Process in batches
            for i in range(0, len(epoch_examples), batch_size):
                batch = epoch_examples[i : i + batch_size]
                self.nlp.update(batch, drop=dropout, sgd=optimizer, losses=losses)

        # Save the trained model
        Path(output_path).mkdir(parents=True, exist_ok=True)
        self.nlp.to_disk(output_path)

        print(f"Model fine-tuning completed and saved to: {output_path}")

    def _get_distilled_label(
        self, start: int, end: int, base_doc: spacy.tokens.Doc
    ) -> str:
        """
        Efficiently find the best geographical entity label using spaCy's char_span.

        Args:
            start: Start character position of the reference span
            end: End character position of the reference span
            base_doc: spaCy Doc processed by the frozen base model

        Returns:
            The distilled geographical entity label or "LOC" as fallback
        """
        # Use spaCy's char_span to efficiently find overlapping span
        span = base_doc.char_span(start, end, alignment_mode="expand")
        if not span:
            return "LOC"  # Default fallback

        return self._span_label(span) or "LOC"

    def _span_label(self, span: spacy.tokens.Span) -> str | None:
        """
        The best geographical label a span carries, if any.

        Entities lying inside the span win. Only when none of them is a wanted
        type is the span scanned token by token, so a span with a matching
        entity is never iterated.

        Args:
            span: The span covering the reference

        Returns:
            A wanted entity label, or None if the span carries none
        """
        return self._first_wanted(
            ent.label_ for ent in span.ents
        ) or self._first_wanted(token.ent_type_ for token in span)

    def _first_wanted(self, labels: t.Iterable[str]) -> str | None:
        """
        The first label that is one of the configured entity types.

        Args:
            labels: Candidate labels, in priority order

        Returns:
            The first wanted label, or None if none matched
        """
        return next((label for label in labels if label in self.entity_types), None)

    def _prepare_training_data(
        self, texts: list[str], references: list[list[tuple[int, int]]]
    ) -> list[Example]:
        """
        Convert documents with reference annotations to spaCy training format.
        Uses label distillation to assign each span the label the base model would choose.

        Args:
            texts: List of document text strings
            references: List of lists of (start, end) position tuples

        Returns:
            List of spaCy Example objects for training
        """
        # Load frozen base pipeline for label distillation
        base_nlp = self._load_spacy_model()

        examples = []

        for text, doc_references in zip(texts, references, strict=True):
            # Create spaCy doc from text (for training)
            doc = self.nlp.make_doc(text)

            # Process document with frozen base model for label distillation
            base_doc = base_nlp(text)

            # Extract entities from references with distilled labels
            entities = []
            for start, end in doc_references:
                # Get distilled label from base model
                entity_label = self._get_distilled_label(start, end, base_doc)
                entities.append((start, end, entity_label))

            # Create training example
            entity_dict = {"entities": entities}
            example = Example.from_dict(doc, entity_dict)
            examples.append(example)

        return examples
