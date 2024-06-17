import logging
import os
from importlib import import_module
from typing import List, Set

import spacy
import torch
from sentence_transformers import SentenceTransformer, util
from tqdm.auto import tqdm

from .geodoc import GeoDoc

# Suppress token length warnings from transformers
logging.getLogger("transformers.tokenization_utils_base").setLevel(logging.ERROR)


class Geoparser:
    def __init__(
        self,
        spacy_model="en_core_web_trf",
        transformer_model="dguzh/geo-all-distilroberta-v1",
        gazetteer="geonames",
    ):
        self.gazetteer = self.setup_gazetteer(gazetteer)
        self.nlp = self.setup_spacy(spacy_model)
        self.transformer = self.setup_transformer(transformer_model)
        self.country_filter = None
        self.feature_filter = None

    def setup_gazetteer(self, gazetteer):

        GAZETTEERS = {"geonames": "geonames.GeoNames"}

        gazetteer_name = gazetteer.lower()

        if gazetteer_name in GAZETTEERS:
            gazetteer_module, gazetteer_class = GAZETTEERS[gazetteer_name].split(".")

            module = import_module("." + gazetteer_module, package="geoparser")
            gazetteer = getattr(module, gazetteer_class)()

            return gazetteer

        else:
            available = ", ".join(GAZETTEERS.keys())
            raise ValueError(
                f"Invalid gazetteer name. Available gazetteers: {available}"
            )

    def setup_spacy(self, spacy_model):
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

    def setup_transformer(self, transformer_model):
        return SentenceTransformer(transformer_model)

    def parse(
        self,
        texts: List[str],
        batch_size=8,
        country_filter: List[str] = None,
        feature_filter: List[str] = None,
    ):
        if not isinstance(texts, list) or not all(
            isinstance(text, str) for text in texts
        ):
            raise TypeError("Input must be a list of strings")

        self.country_filter = country_filter
        self.feature_filter = feature_filter

        print("Toponym Recognition...")
        docs = list(
            tqdm(
                self.nlp.pipe(texts, batch_size=batch_size),
                total=len(texts),
                desc="Batches",
            )
        )

        print("Toponym Resolution...")
        self.resolve(docs, batch_size=batch_size)

        return docs

    def resolve(self, docs: List[GeoDoc], batch_size=8):

        candidate_ids = set()
        for doc in docs:
            for toponym in doc.toponyms:
                candidate_ids.update(toponym.candidates)

        if candidate_ids:
            candidate_ids = list(candidate_ids)
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
            candidate_embeddings_lookup = dict(zip(candidate_ids, candidate_embeddings))

            toponym_contexts = [
                toponym.context.text for doc in docs for toponym in doc.toponyms
            ]
            toponym_embeddings = self.transformer.encode(
                toponym_contexts,
                batch_size=batch_size,
                show_progress_bar=True,
                convert_to_tensor=True,
            )

            toponym_index = 0
            for doc in docs:
                for toponym in doc.toponyms:
                    candidate_ids = toponym.candidates
                    candidate_embeddings = [
                        candidate_embeddings_lookup[candidate_id]
                        for candidate_id in candidate_ids
                    ]
                    if candidate_embeddings:
                        candidate_embeddings = torch.stack(candidate_embeddings)
                        similarities = util.cos_sim(
                            toponym_embeddings[toponym_index], candidate_embeddings
                        )
                        predicted_index = torch.argmax(similarities).item()
                        predicted_id = candidate_ids[predicted_index]
                        toponym._.loc_id = predicted_id
                        score = float(similarities[0][predicted_index])
                        toponym._.loc_score = score

                    toponym_index += 1
