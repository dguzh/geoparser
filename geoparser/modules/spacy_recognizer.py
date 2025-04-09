from typing import List, Set, Tuple

import spacy

from geoparser.modules.interfaces import AbstractRecognitionModule


class SpacyRecognitionModule(AbstractRecognitionModule):
    """
    A recognition module that uses spaCy to identify toponyms in document text.

    This module identifies location-based named entities like GPE (geopolitical entity),
    LOC (location), and FAC (facility) as potential toponyms.
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
            entity_types: Set of spaCy entity types to consider as toponyms
                          (default: {"GPE", "LOC", "FAC"})
        """
        # Initialize parent with the parameters
        super().__init__(model_name=model_name, entity_types=entity_types)

        # Store instance attributes directly from parameters
        self.model_name = model_name
        self.entity_types = entity_types

        # Load spaCy model
        self.nlp = spacy.load(self.model_name)

        # Disable non-NER components to optimize performance
        pipe_components = [
            "tok2vec",
            "tagger",
            "parser",
            "attribute_ruler",
            "lemmatizer",
        ]
        self.nlp.disable_pipes(
            *[p for p in pipe_components if p in self.nlp.pipe_names]
        )

    def predict_toponyms(
        self, document_texts: List[str]
    ) -> List[List[Tuple[int, int]]]:
        """
        Identify toponyms (location entities) in multiple documents using spaCy.

        Args:
            document_texts: List of document texts to process

        Returns:
            List of lists of tuples containing (start, end) positions of toponyms.
            Each inner list corresponds to toponyms found in one document.
        """
        results = []

        # Process documents in batches using spaCy's nlp.pipe for efficiency
        docs = list(self.nlp.pipe(document_texts))

        # Extract toponym offsets for each document
        for doc in docs:
            # Find all entities that match our entity types of interest
            toponyms = [
                (ent.start_char, ent.end_char)
                for ent in doc.ents
                if ent.label_ in self.entity_types
            ]
            results.append(toponyms)

        return results
