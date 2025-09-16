import typing as t
from typing import List, Set, Tuple

import spacy

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
            "tok2vec",
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
