from __future__ import annotations

import typing as t
import warnings

import spacy
import torch
from sentence_transformers import SentenceTransformer, util
from tqdm.auto import tqdm

from geoparser.constants import (
    DEFAULT_GAZETTEER,
    DEFAULT_SPACY_MODEL,
    DEFAULT_TRANSFORMER_MODEL,
    GAZETTEERS,
)
from geoparser.gazetteers.gazetteer import Gazetteer
from geoparser.geodoc import GeoDoc

# Suppress FutureWarning from the thinc.shims.pytorch module until they update their code
warnings.filterwarnings(
    "ignore",
    category=FutureWarning,
    message="You are using `torch.load` with `weights_only=False`",
    module="thinc.shims.pytorch",
)


class Geoparser:
    """Main class for performing geoparsing operations."""

    def __init__(
        self,
        spacy_model: str = DEFAULT_SPACY_MODEL,
        transformer_model: str = DEFAULT_TRANSFORMER_MODEL,
        gazetteer: str = DEFAULT_GAZETTEER,
    ):
        """
        Initialize the Geoparser with specified spaCy model, transformer model, and gazetteer.

        Args:
            spacy_model (str): Name of the spaCy model to use for NER.
            transformer_model (str): Name or path of the SentenceTransformer model.
            gazetteer (str): Name of the gazetteer to use.
        """
        self.gazetteer = self.setup_gazetteer(gazetteer)
        self.nlp = self.setup_spacy(spacy_model)
        self.transformer = self.setup_transformer(transformer_model)

    def setup_gazetteer(self, gazetteer: str) -> Gazetteer:
        """
        Set up the gazetteer.

        Args:
            gazetteer (str): Name of the gazetteer to initialize.

        Returns:
            Gazetteer: An instance of the specified Gazetteer.

        Raises:
            ValueError: If the gazetteer name is invalid.
        """
        if gazetteer in GAZETTEERS:
            gazetteer = GAZETTEERS[gazetteer.lower()]()
            return gazetteer

        else:
            available = ", ".join(GAZETTEERS.keys())
            raise ValueError(
                f"Invalid gazetteer name. Available gazetteers: {available}"
            )

    def setup_spacy(self, spacy_model: str) -> spacy.language.Language:
        """
        Set up the spaCy NLP pipeline.

        Args:
            spacy_model (str): Name of the spaCy model to load.

        Returns:
            spacy.language.Language: The loaded spaCy NLP pipeline.

        Raises:
            OSError: If the spaCy model is not found.
        """
        if not spacy.util.is_package(spacy_model):
            raise OSError(
                f"spaCy model '{spacy_model}' not found. Run the following command to install it:\npython -m spacy download {spacy_model}"
            )

        spacy.prefer_gpu()

        nlp = spacy.load(spacy_model)
        nlp.make_doc = lambda text: GeoDoc(
            self,
            nlp.vocab,
            words=[t.text for t in nlp.tokenizer(text)],
            spaces=[t.whitespace_ for t in nlp.tokenizer(text)],
        )
        return nlp

    def setup_transformer(self, transformer_model: str) -> SentenceTransformer:
        """
        Set up the SentenceTransformer model.

        Args:
            transformer_model (str): Name or path of the transformer model to load.

        Returns:
            SentenceTransformer: The loaded SentenceTransformer model.
        """
        return SentenceTransformer(transformer_model)

    def parse(
        self,
        texts: t.List[str],
        batch_size: int = 8,
        filter: t.Optional[t.Dict[str, t.List[str]]] = None,
    ) -> t.List[GeoDoc]:
        """
        Perform full geoparsing (recognition and resolution) on a list of texts.

        Args:
            texts (List[str]): List of input texts to geoparse.
            batch_size (int): Batch size for processing texts.
            filter (Optional[Dict[str, List[str]]], optional): Filter to restrict candidate selection.

        Returns:
            List[GeoDoc]: List of GeoDoc objects containing geoparsed information.

        Raises:
            TypeError: If input is not a list of strings.
        """
        if not isinstance(texts, list) or not all(
            isinstance(text, str) for text in texts
        ):
            raise TypeError("Input must be a list of strings")

        print("Toponym Recognition...")
        docs = self.recognize(texts, batch_size=batch_size)

        print("Toponym Resolution...")
        docs = self.resolve(docs, batch_size=batch_size, filter=filter)
        return docs

    def recognize(self, texts: t.List[str], batch_size: int = 8) -> t.List[GeoDoc]:
        """
        Perform toponym recognition on a list of texts.

        Args:
            texts (List[str]): List of input texts.
            batch_size (int): Batch size for processing texts.

        Returns:
            List[GeoDoc]: List of GeoDoc objects with recognized toponyms.
        """
        docs = list(
            tqdm(
                self.nlp.pipe(texts, batch_size=batch_size),
                total=len(texts),
                desc="Batches",
            )
        )
        return docs

    def resolve(
        self,
        docs: t.List[GeoDoc],
        batch_size: int = 8,
        filter: t.Optional[t.Dict[str, t.List[str]]] = None,
    ) -> t.List[GeoDoc]:
        """
        Perform toponym resolution on a list of GeoDocs.

        Args:
            docs (List[GeoDoc]): List of GeoDoc objects with recognized toponyms.
            batch_size (int): Batch size for processing.
            filter (Optional[Dict[str, List[str]]], optional): Filter to restrict candidate selection.

        Returns:
            List[GeoDoc]: List of GeoDoc objects with resolved toponyms.
        """
        if candidate_ids := self._get_candidate_ids(docs, filter=filter):
            candidate_embeddings_lookup = self._get_candidate_embeddings_lookup(
                candidate_ids, batch_size
            )
            toponym_embeddings = self._get_toponym_embeddings(docs, batch_size)

            toponym_index = 0
            for doc in docs:
                for toponym in doc.toponyms:
                    candidates = toponym.get_candidates(filter=filter)
                    if candidates:
                        toponym._.loc_id, toponym._.loc_score = self._resolve_toponym(
                            candidate_embeddings_lookup,
                            candidates,
                            toponym_embeddings,
                            toponym_index,
                        )
                    toponym_index += 1
        return docs

    def _get_candidate_ids(
        self, docs: t.List[GeoDoc], filter: t.Optional[t.Dict[str, t.List[str]]] = None
    ) -> t.List[str]:
        """
        Collect all candidate location IDs from the toponyms in a list of GeoDocs.

        Args:
            docs (List[GeoDoc]): List of GeoDoc objects.
            filter (Optional[Dict[str, List[str]]], optional): Filter to restrict candidate selection.

        Returns:
            List[str]: List of unique candidate location IDs.
        """
        candidate_ids = set()
        for doc in docs:
            for toponym in doc.toponyms:
                candidates = toponym.get_candidates(filter=filter)
                candidate_ids.update(candidates)
        return list(candidate_ids)

    def _get_candidate_embeddings_lookup(
        self, candidate_ids: t.List[str], batch_size: int = 8
    ) -> t.Dict[str, torch.Tensor]:
        """
        Generate embeddings for candidate locations.

        Args:
            candidate_ids (List[str]): List of candidate location IDs.
            batch_size (int): Batch size for encoding.

        Returns:
            Dict[str, torch.Tensor]: Dictionary mapping candidate IDs to embeddings.
        """
        candidate_descriptions = [
            self.gazetteer.get_location_description(location)
            for location in self.gazetteer.query_locations(candidate_ids)
        ]
        candidate_embeddings = self.transformer.encode(
            candidate_descriptions,
            batch_size=batch_size,
            show_progress_bar=True,
            convert_to_tensor=True,
        )
        return dict(zip(candidate_ids, candidate_embeddings))

    def _get_toponym_embeddings(
        self, docs: t.List[GeoDoc], batch_size: int = 8
    ) -> torch.Tensor:
        """
        Generate embeddings for all toponyms in a list of GeoDocs.

        Args:
            docs (List[GeoDoc]): List of GeoDoc objects.
            batch_size (int): Batch size for encoding.

        Returns:
            torch.Tensor: Tensor containing embeddings for toponym contexts.
        """
        toponym_contexts = [
            toponym.context.text for doc in docs for toponym in doc.toponyms
        ]
        toponym_embeddings = self.transformer.encode(
            toponym_contexts,
            batch_size=batch_size,
            show_progress_bar=True,
            convert_to_tensor=True,
        )
        return toponym_embeddings

    def _resolve_toponym(
        self,
        candidate_embeddings_lookup: t.Dict[str, torch.Tensor],
        candidate_ids: t.List[str],
        toponym_embeddings: torch.Tensor,
        toponym_index: int,
    ) -> t.Tuple[str, float]:
        """
        Resolve a single toponym by comparing embeddings.

        Args:
            candidate_embeddings_lookup (Dict[str, torch.Tensor]): Lookup of candidate embeddings.
            candidate_ids (List[str]): List of candidate IDs for the toponym.
            toponym_embeddings (torch.Tensor): Embeddings of toponym contexts.
            toponym_index (int): Index of the current toponym in embeddings.

        Returns:
            Tuple[str, float]: The predicted candidate ID and its similarity score.
        """
        candidate_embeddings = torch.stack(
            [
                candidate_embeddings_lookup[candidate_id]
                for candidate_id in candidate_ids
            ]
        )
        similarities = util.cos_sim(
            toponym_embeddings[toponym_index], candidate_embeddings
        )
        predicted_index = torch.argmax(similarities).item()
        predicted_id = candidate_ids[predicted_index]
        score = float(similarities[0][predicted_index])
        return predicted_id, score
