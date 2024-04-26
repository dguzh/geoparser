import os
import re
import pickle
import unicodedata
import logging
import spacy
from tqdm.auto import tqdm
from typing import List, Set
from sentence_transformers import SentenceTransformer, util
import torch

from entities import Document, Toponym, Location
from gazetteer import Gazetteer

# Suppress token length warnings from transformers
logging.getLogger("transformers.tokenization_utils_base").setLevel(logging.ERROR)

class Geoparser:
    def __init__(self, spacy_model='en_core_web_trf', transformer_model='models/all-distilroberta-v1',
                 index_file='index.pkl', geonames_file='geonames/allCountries.txt'):
        self.ensure_spacy_model(spacy_model)
        self.nlp = spacy.load(spacy_model)
        self.transformer = SentenceTransformer(transformer_model)
        self.index_file = index_file
        self.geonames_file = geonames_file
        self.index = self.load_index()
        self.tokenizer = self.transformer.tokenizer
        self.model_max_length = self.tokenizer.model_max_length

    def ensure_spacy_model(self, model_name):
        if not spacy.util.is_package(model_name):
            print(f"Downloading spaCy model '{model_name}'...")
            spacy.cli.download(model_name)

    def normalize_name(self, name):
        name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode('ascii')
        name = re.sub(r"[^\w\s]", "", name)  # remove all punctuation
        name = re.sub(r"\s+", " ", name).strip()  # normalize whitespaces and strip
        return name.lower()  # convert to lowercase

    def load_index(self):
        if os.path.exists(self.index_file):
            with open(self.index_file, 'rb') as file:
                return pickle.load(file)
        else:
            index = self.build_index()
            with open(self.index_file, 'wb') as file:
                pickle.dump(index, file)
            return index

    def build_index(self):
        index = {}
        with open(self.geonames_file, 'r', encoding='utf-8') as file:
            total_lines = sum(1 for line in file)
        with open(self.geonames_file, 'r', encoding='utf-8') as file:
            for line in tqdm(file, total=total_lines, desc="Building index", unit=" lines"):
                columns = line.strip().split('\t')
                geonameid = int(columns[0])
                names = [columns[1]] + columns[3].split(',')
                for name in names:
                    normalized_name = self.normalize_name(name)
                    if normalized_name:
                        if normalized_name not in index:
                            index[normalized_name] = set()
                        index[normalized_name].add(geonameid)
        return index

    def parse(self, texts: List[str]):
        documents = [Document(text) for text in texts]
        for document in documents:
            self.extract_toponyms(document)
        self.resolve_toponyms(documents)
        return documents

    def extract_toponyms(self, document: Document):
        doc = self.nlp(document.text)
        sentences = list(doc.sents)
        total_tokens = len(self.tokenizer.tokenize(document.text))

        for ent in doc.ents:
            if ent.label_ in ['GPE', 'LOC', 'FAC']:
                text, start_char, end_char = self.clean_ent(ent)
                context = document.text if total_tokens <= self.model_max_length else self.truncate_context(sentences, ent)
                document.toponyms.append(Toponym(text, start_char, end_char, context))

    def clean_ent(self, ent):
        # remove leading lowercase 'the'
        original_text = ent.text
        new_text = re.sub(r"^the\s+", "", original_text)
        if new_text != original_text:
            new_text = new_text.lstrip()
            start_char = ent.start_char + (len(original_text) - len(new_text))
        else:
            start_char = ent.start_char

        # remove trailing possessive 's
        original_text = new_text
        new_text = re.sub(r"\'s$", "", original_text)
        if new_text != original_text:
            new_text = new_text.rstrip()
            end_char = start_char + len(new_text)
        else:
            end_char = start_char + len(original_text)

        return new_text, start_char, end_char

    def truncate_context(self, sentences, ent):
        # Find the sentence containing the toponym
        target_sentence = next((s for s in sentences if s.start_char <= ent.start_char and s.end_char >= ent.end_char), None)
        if not target_sentence:
            return ""

        target_index = sentences.index(target_sentence)
        token_limit = self.model_max_length
        context_sentences = [target_sentence.text]
        tokens_count = len(self.tokenizer.tokenize(target_sentence.text))

        # Expand context by adding sentences before and after the toponym sentence
        i, j = target_index, target_index
        while True:
            expanded = False
            if i > 0:
                prev_tokens = self.tokenizer.tokenize(sentences[i - 1].text)
                if tokens_count + len(prev_tokens) < token_limit:
                    context_sentences.insert(0, sentences[i - 1].text)
                    tokens_count += len(prev_tokens)
                    i -= 1
                    expanded = True

            if j < len(sentences) - 1:
                next_tokens = self.tokenizer.tokenize(sentences[j + 1].text)
                if tokens_count + len(next_tokens) < token_limit:
                    context_sentences.append(sentences[j + 1].text)
                    tokens_count += len(next_tokens)
                    j += 1
                    expanded = True

            # Break if no sentences were added in the last iteration
            if not expanded:
                break

        return ' '.join(context_sentences)

    def query_index(self, toponym: str) -> set:
        normalized_toponym = self.normalize_name(toponym)
        return self.index.get(normalized_toponym, set())

    def resolve_toponyms(self, documents: List[Document]):
        all_candidates = set()
        for document in documents:
            for toponym in document.toponyms:
                candidates = self.query_index(toponym.name)
                all_candidates.update(candidates)
                toponym.candidates = candidates

        if all_candidates:
            gazetteer = Gazetteer()
            gazetteer.load(all_candidates)

            pseudotexts = gazetteer.data['pseudotext'].tolist()

            candidate_embeddings = self.transformer.encode(pseudotexts, batch_size=8, show_progress_bar=True, convert_to_tensor=True)

            candidate_embeddings_lookup = dict(zip(gazetteer.data['geonameid'], candidate_embeddings))

            contexts = [toponym.context for document in documents for toponym in document.toponyms]

            toponym_embeddings = self.transformer.encode(contexts, batch_size=8, show_progress_bar=True, convert_to_tensor=True)

            toponym_index = 0
            for document in documents:
                for toponym in document.toponyms:
                    candidates = list(toponym.candidates)
                    candidate_embeddings = [candidate_embeddings_lookup[geonameid] for geonameid in candidates if geonameid in candidate_embeddings_lookup]

                    if candidate_embeddings:
                        candidate_embeddings = torch.stack(candidate_embeddings)
                        similarities = util.cos_sim(toponym_embeddings[toponym_index], candidate_embeddings)
                        predicted_index = torch.argmax(similarities).item()
                        predicted_geonameid = candidates[predicted_index]

                        # Step 7: Create a Location object for the best match and assign to the toponym
                        predicted_location = gazetteer.data.loc[gazetteer.data['geonameid'] == predicted_geonameid].iloc[0]
                        toponym.location = Location(
                            geonameid=predicted_geonameid,
                            name=predicted_location['name'],
                            admin2_geonameid=predicted_location['admin2_geonameid'],
                            admin2_name=predicted_location['admin2_name'],
                            admin1_geonameid=predicted_location['admin1_geonameid'],
                            admin1_name=predicted_location['admin1_name'],
                            country_geonameid=predicted_location['country_geonameid'],
                            country_name=predicted_location['country_name'],
                            feature_name=predicted_location['feature_name'],
                            latitude=predicted_location['latitude'],
                            longitude=predicted_location['longitude'],
                            elevation=predicted_location['elevation'],
                            population=predicted_location['population']
                        )
                    toponym_index += 1