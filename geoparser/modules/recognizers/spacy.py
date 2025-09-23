import random
import typing as t
from pathlib import Path
from typing import List, Set, Tuple, Union

import spacy
from spacy.training import Example

from geoparser.modules.recognizers import Recognizer

if t.TYPE_CHECKING:
    from geoparser.db.models import Document


class SpacyRecognizer(Recognizer):
    """
    A recognition module that uses spaCy to identify references in document text.

    This module identifies location-based named entities like GPE (geopolitical entity),
    LOC (location), and FAC (facility) as potential references.
    """

    NAME = "SpacyRecognizer"

    def __init__(
        self,
        model_name: str = "en_core_web_sm",
        entity_types: Set[str] = {"GPE", "LOC", "FAC"},
    ):
        """
        Initialize the SpaCy recognition module.

        Args:
            model_name: spaCy model to use (default: "en_core_web_sm")
            entity_types: Set of spaCy entity types to consider as references
                          (default: {"GPE", "LOC", "FAC"})
        """
        # Initialize parent with the parameters
        super().__init__(model_name=model_name, entity_types=entity_types)

        # Store instance attributes directly from parameters
        self.model_name = model_name
        self.entity_types = entity_types

        # Load spaCy model with optimized pipeline
        self.nlp = self._load_spacy_model()

    def _load_spacy_model(self) -> spacy.language.Language:
        """
        Load and configure the spaCy model with optimized pipeline.

        Loads the specified model and disables unnecessary pipeline components
        to optimize performance for NER tasks.

        Returns:
            Configured spaCy Language model
        """
        # Load spaCy model
        nlp = spacy.load(self.model_name)

        # Disable non-NER components to optimize performance
        pipe_components = [
            "tagger",
            "parser",
            "attribute_ruler",
            "lemmatizer",
        ]
        nlp.disable_pipes(*[p for p in pipe_components if p in nlp.pipe_names])
        return nlp

    def predict_references(
        self, documents: List["Document"]
    ) -> List[List[Tuple[int, int]]]:
        """
        Identify references (location entities) in multiple documents using spaCy.

        Args:
            documents: List of Document ORM objects to process

        Returns:
            List of lists of tuples containing (start, end) positions of references.
            Each inner list corresponds to references found in one document.
        """
        results = []

        # Extract document texts for batch processing
        document_texts = [doc.text for doc in documents]

        # Process documents in batches using spaCy's nlp.pipe for efficiency
        docs = list(self.nlp.pipe(document_texts))

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
        documents: List["Document"],
        output_path: Union[str, Path],
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
            documents: List of Document objects containing reference annotations
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
        examples = self._prepare_training_data(documents)

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
        for epoch in range(epochs):
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

        if span:
            # Check entities that overlap with our span
            for ent in span.ents:
                if ent.label_ in self.entity_types:
                    return ent.label_

            # If no entities in the exact span, check if span overlaps with any entity
            for token in span:
                if token.ent_type_ in self.entity_types:
                    return token.ent_type_

        return "LOC"  # Default fallback

    def _prepare_training_data(self, documents: List["Document"]) -> List[Example]:
        """
        Convert documents with reference annotations to spaCy training format.
        Uses label distillation to assign each span the label the base model would choose.

        Args:
            documents: List of Document objects with reference annotations

        Returns:
            List of spaCy Example objects for training
        """
        # Load frozen base pipeline for label distillation
        base_nlp = self._load_spacy_model()

        examples = []

        for document in documents:
            # Create spaCy doc from text (for training)
            doc = self.nlp.make_doc(document.text)

            # Process document with frozen base model for label distillation
            base_doc = base_nlp(document.text)

            # Extract entities from references with distilled labels
            entities = []
            for reference in document.references:
                # Get distilled label from base model
                entity_label = self._get_distilled_label(
                    reference.start, reference.end, base_doc
                )
                entities.append((reference.start, reference.end, entity_label))

            # Create training example
            entity_dict = {"entities": entities}
            example = Example.from_dict(doc, entity_dict)
            examples.append(example)

        return examples
