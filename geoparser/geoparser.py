import logging

import spacy
import torch
from sentence_transformers import SentenceTransformer, util
from tqdm.auto import tqdm

from geoparser.constants import DEFAULT_TRANSFORMER_MODEL, GAZETTEERS
from geoparser.gazetteer import Gazetteer
from geoparser.geodoc import GeoDoc

# Suppress token length warnings from transformers
logging.getLogger("transformers.tokenization_utils_base").setLevel(logging.ERROR)


class Geoparser:
    def __init__(
        self,
        spacy_model: str = "en_core_web_trf",
        transformer_model: str = DEFAULT_TRANSFORMER_MODEL,
        gazetteer: str = "geonames",
    ):
        self.gazetteer = self.setup_gazetteer(gazetteer)
        self.nlp = self.setup_spacy(spacy_model)
        self.transformer = self.setup_transformer(transformer_model)

    def setup_gazetteer(self, gazetteer: str) -> type[Gazetteer]:

        if gazetteer in GAZETTEERS:
            gazetteer = GAZETTEERS[gazetteer.lower()]()
            return gazetteer

        else:
            available = ", ".join(GAZETTEERS.keys())
            raise ValueError(
                f"Invalid gazetteer name. Available gazetteers: {available}"
            )

    def setup_spacy(self, spacy_model: str) -> type[spacy.language.Language]:
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
        return SentenceTransformer(transformer_model)

    def parse(
        self,
        texts: list[str],
        batch_size: int = 8,
    ) -> list[GeoDoc]:
        if not isinstance(texts, list) or not all(
            isinstance(text, str) for text in texts
        ):
            raise TypeError("Input must be a list of strings")

        print("Toponym Recognition...")
        docs = self.recognize(texts, batch_size=batch_size)

        print("Toponym Resolution...")
        docs = self.resolve(docs, batch_size=batch_size)
        return docs

    def recognize(self, texts: list[str], batch_size: int = 8) -> list[GeoDoc]:
        docs = list(
            tqdm(
                self.nlp.pipe(texts, batch_size=batch_size),
                total=len(texts),
                desc="Batches",
            )
        )
        return docs

    def resolve(self, docs: list[GeoDoc], batch_size: int = 8) -> list[GeoDoc]:
        if candidate_ids := self.get_candidate_ids(docs):
            candidate_embeddings_lookup = self.get_candidate_embeddings_lookup(
                candidate_ids, batch_size
            )
            toponym_embeddings = self.get_toponym_embeddings(docs, batch_size)

            toponym_index = 0
            for doc in docs:
                for toponym in doc.toponyms:
                    if toponym.candidates:
                        toponym._.loc_id, toponym._.loc_score = self.resolve_toponym(
                            candidate_embeddings_lookup,
                            toponym.candidates,
                            toponym_embeddings,
                            toponym_index,
                        )
                    toponym_index += 1
        return docs

    def get_candidate_ids(self, docs: list[GeoDoc]) -> list[int]:
        candidate_ids = set()
        for doc in docs:
            for toponym in doc.toponyms:
                candidate_ids.update(toponym.candidates)
        return list(candidate_ids)

    def get_candidate_embeddings_lookup(
        self, candidate_ids: list[int], batch_size: int = 8
    ) -> dict[str, torch.Tensor]:
        candidate_descriptions = [
            self.gazetteer.get_location_description(location)
            for location in self.gazetteer.query_location_info(candidate_ids)
        ]
        candidate_embeddings = self.transformer.encode(
            candidate_descriptions,
            batch_size=batch_size,
            show_progress_bar=True,
            convert_to_tensor=True,
        )
        return dict(zip(candidate_ids, candidate_embeddings))

    def get_toponym_embeddings(
        self, docs: list[GeoDoc], batch_size: int = 8
    ) -> torch.Tensor:
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

    def resolve_toponym(
        self,
        candidate_embeddings_lookup: dict[str, torch.Tensor],
        candidate_ids: list[int],
        toponym_embeddings: torch.Tensor,
        toponym_index: int,
    ) -> tuple[int, float]:
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
