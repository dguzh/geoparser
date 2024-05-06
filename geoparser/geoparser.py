import os
import re
import logging
import spacy
import sqlite3
from tqdm.auto import tqdm
from typing import List, Set
from sentence_transformers import SentenceTransformer, util
from appdirs import user_data_dir
import torch

from .entities import Document, Toponym, Location

# Suppress token length warnings from transformers
logging.getLogger("transformers.tokenization_utils_base").setLevel(logging.ERROR)

class Geoparser:
    def __init__(self, spacy_model='en_core_web_trf', transformer_model='dguzh/geo-all-distilroberta-v1'):
        self.db_path = os.path.join(user_data_dir('geoparser'), 'geonames.db')
        self.ensure_spacy_model(spacy_model)
        self.nlp = spacy.load(spacy_model)
        self.transformer = SentenceTransformer(transformer_model)
        self.tokenizer = self.transformer.tokenizer
        self.model_max_length = self.tokenizer.model_max_length

    def ensure_spacy_model(self, model_name):
        if not spacy.util.is_package(model_name):
            print(f"Downloading spaCy model '{model_name}'...")
            spacy.cli.download(model_name)

    def parse(self, texts: List[str], country_filter: List[str] = None, feature_filter: List[str] = None):
        if not isinstance(texts, list) or not all(isinstance(text, str) for text in texts):
            raise TypeError("Input must be a list of strings")

        documents = [Document(text) for text in texts]
        for document in documents:
            self.extract_toponyms(document)
        self.resolve_toponyms(documents, country_filter, feature_filter)
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
        new_text = re.sub(r"^the\s+", "", original_text).lstrip('"')
        if new_text != original_text:
            new_text = new_text.lstrip()
            start_char = ent.start_char + (len(original_text) - len(new_text))
        else:
            start_char = ent.start_char

        # remove trailing possessive 's
        original_text = new_text
        new_text = re.sub(r"\'s$", "", original_text).rstrip('"')
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

    def resolve_toponyms(self, documents: List[Document], country_filter: List[str] = None, feature_filter: List[str] = None):
        all_candidates = set()
        for document in documents:
            for toponym in document.toponyms:
                candidates = self.fetch_candidates(toponym.name, country_filter, feature_filter)
                all_candidates.update(candidates)
                toponym.candidates = candidates

        if all_candidates:
            all_candidates = list(all_candidates)
            pseudotexts = self.fetch_pseudotexts(all_candidates)
            candidate_embeddings = self.transformer.encode(pseudotexts, batch_size=8, show_progress_bar=True, convert_to_tensor=True)
            candidate_embeddings_lookup = dict(zip(all_candidates, candidate_embeddings))

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
                        predicted_location = self.fetch_location_attributes(predicted_geonameid)
                        toponym.location = Location(**predicted_location)

                    toponym_index += 1

    def execute_query(self, query, params=None):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            return cursor.fetchall()
                    
    def fetch_candidates(self, toponym, country_filter=None, feature_filter=None):

        toponym = re.sub(r"\"", "", toponym).strip()

        toponym = ' '.join([f'"{word}"' for word in toponym.split()])

        base_query = '''
            WITH MinRankAllCountries AS (
                SELECT MIN(rank) AS MinRank FROM allCountries_fts WHERE allCountries_fts MATCH ?
            ),
            MinRankAlternateNames AS (
                SELECT MIN(rank) AS MinRank FROM alternateNames_fts WHERE alternateNames_fts MATCH ?
            ),
            CombinedResults AS (
                SELECT allCountries_fts.rowid as geonameid, allCountries_fts.rank as rank
                FROM allCountries_fts
                WHERE allCountries_fts MATCH ?

                UNION

                SELECT alternateNames.geonameid, alternateNames_fts.rank as rank
                FROM alternateNames_fts
                JOIN alternateNames ON alternateNames_fts.rowid = alternateNames.alternateNameId
                WHERE alternateNames_fts MATCH ?
            )
            SELECT ac.geonameid
            FROM CombinedResults cr
            JOIN allCountries ac ON cr.geonameid = ac.geonameid
            WHERE (cr.rank = (SELECT MinRank FROM MinRankAllCountries)
                   OR cr.rank = (SELECT MinRank FROM MinRankAlternateNames))
        '''

        where_clauses = []
        params = [toponym, toponym, toponym, toponym]

        # Adding filters for country codes
        if country_filter:
            where_clauses.append(f"ac.country_code IN ({','.join(['?' for _ in country_filter])})")
            params.extend(country_filter)

        # Adding filters for feature classes
        if feature_filter:
            where_clauses.append(f"ac.feature_class IN ({','.join(['?' for _ in feature_filter])})")
            params.extend(feature_filter)

        # Append additional filters if present
        if where_clauses:
            base_query += f" AND {' AND '.join(where_clauses)}"

        base_query += " GROUP BY ac.geonameid ORDER BY cr.rank"

        # Execute query with the constructed parameters
        result = self.execute_query(base_query, tuple(params))
        return [row[0] for row in result]

    def fetch_pseudotexts(self, candidate_ids, batch_size=500):
        chunks = [candidate_ids[i:i + batch_size] for i in range(0, len(candidate_ids), batch_size)]
        results_dict = {}
        for chunk in chunks:
            placeholders = ', '.join(['?' for _ in chunk])
            query = f"""
            SELECT
                geonameid,
                name || 
                CASE 
                    WHEN feature_name IS NOT NULL THEN ' (' || feature_name || ')'
                    ELSE ''
                END || 
                CASE 
                    WHEN admin2_name IS NOT NULL OR admin1_name IS NOT NULL OR country_name IS NOT NULL THEN ' in '
                    ELSE ''
                END ||
                COALESCE(admin2_name || ', ', '') ||
                COALESCE(admin1_name || ', ', '') ||
                COALESCE(country_name, '') AS pseudotext
            FROM allCountries
            LEFT JOIN countryInfo ON allCountries.country_code = countryInfo.ISO
            LEFT JOIN admin1CodesASCII ON countryInfo.ISO || '.' || allCountries.admin1_code = admin1CodesASCII.admin1_full_code
            LEFT JOIN admin2Codes ON countryInfo.ISO || '.' || allCountries.admin1_code || '.' || allCountries.admin2_code = admin2Codes.admin2_full_code
            LEFT JOIN featureCodes ON allCountries.feature_class || '.' || allCountries.feature_code = featureCodes.feature_full_code
            WHERE allCountries.geonameid IN ({placeholders})
            """
            result = self.execute_query(query, chunk)
            for geonameid, pseudotext in result:
                results_dict[geonameid] = pseudotext

        pseudotexts = [results_dict.get(id, "") for id in candidate_ids]
        return pseudotexts

    def fetch_location_attributes(self, geonameid):
        query = """
        SELECT geonameid, name, admin2_geonameid, admin2_name, admin1_geonameid, admin1_name, country_geonameid, country_name, feature_name, latitude, longitude, elevation, population
        FROM allCountries
        LEFT JOIN countryInfo ON allCountries.country_code = countryInfo.ISO
        LEFT JOIN admin1CodesASCII ON countryInfo.ISO || '.' || allCountries.admin1_code = admin1CodesASCII.admin1_full_code
        LEFT JOIN admin2Codes ON countryInfo.ISO || '.' || allCountries.admin1_code || '.' || allCountries.admin2_code = admin2Codes.admin2_full_code
        LEFT JOIN featureCodes ON allCountries.feature_class || '.' || allCountries.feature_code = featureCodes.feature_full_code
        WHERE geonameid = ?
        """
        result = self.execute_query(query, (geonameid,))
        if result:
            row = result[0]
            return {
                'geonameid': row[0],
                'name': row[1],
                'admin2_geonameid': row[2],
                'admin2_name': row[3],
                'admin1_geonameid': row[4],
                'admin1_name': row[5],
                'country_geonameid': row[6],
                'country_name': row[7],
                'feature_name': row[8],
                'latitude': row[9],
                'longitude': row[10],
                'elevation': row[11],
                'population': row[12]
            }
        return {}
        