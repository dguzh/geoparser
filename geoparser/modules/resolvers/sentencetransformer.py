import typing as t
from typing import Dict, List, Tuple

import spacy
import torch
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer

from geoparser.gazetteerv2.gazetteer import Gazetteer
from geoparser.modules.resolvers.resolver import Resolver

if t.TYPE_CHECKING:
    from geoparser.db.models import Reference
    from geoparser.db.models.feature import Feature


class SentenceTransformerResolver(Resolver):
    """
    A resolver that uses SentenceTransformer to map reference contexts to gazetteer candidates.

    This resolver extracts contextual information around each reference, generates embeddings
    for the context, retrieves candidate features from the gazetteer, generates location
    descriptions and embeddings for candidates, and finds the best match using cosine similarity.
    """

    NAME = "SentenceTransformerResolver"

    # Gazetteer-specific attribute mappings for location descriptions
    GAZETTEER_ATTRIBUTE_MAP = {
        "geonames": {
            "name": "name",
            "type": "feature_name",
            "level1": "country_name",
            "level2": "admin1_name",
            "level3": "admin2_name",
        },
        "swissnames3d": {
            "name": "NAME",
            "type": "OBJEKTART",
            "level1": "KANTON_NAME",
            "level2": "BEZIRK_NAME",
            "level3": "GEMEINDE_NAME",
        },
    }

    def __init__(
        self,
        model_name: str = "dguzh/geo-all-MiniLM-L6-v2",
        gazetteer_name: str = "geonames",
        max_candidates: int = 100,
        similarity_threshold: float = 0.0,
    ):
        """
        Initialize the SentenceTransformerResolver.

        Args:
            model_name: HuggingFace model name for SentenceTransformer
            gazetteer_name: Name of the gazetteer to search
            max_candidates: Maximum number of candidates to retrieve per reference
            similarity_threshold: Minimum similarity threshold for matches
        """
        # Initialize parent with the parameters
        super().__init__(
            model_name=model_name,
            gazetteer_name=gazetteer_name,
            max_candidates=max_candidates,
            similarity_threshold=similarity_threshold,
        )

        # Store instance attributes directly from parameters
        self.model_name = model_name
        self.gazetteer_name = gazetteer_name
        self.max_candidates = max_candidates
        self.similarity_threshold = similarity_threshold

        # Initialize transformer and tokenizer
        self.transformer = SentenceTransformer(model_name)
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)

        # Initialize spaCy model for sentence splitting
        self.nlp = spacy.load("xx_sent_ud_sm")

        # Initialize gazetteer
        self.gazetteer = Gazetteer(gazetteer_name)

        # Caches for embeddings to avoid recomputation
        self.description_cache: Dict[str, str] = {}
        self.embedding_cache: Dict[str, torch.Tensor] = {}

    def predict_referents(
        self, references: List["Reference"]
    ) -> List[List[Tuple[str, str]]]:
        """
        Predict referents for multiple references using SentenceTransformer embeddings.

        Args:
            references: List of Reference ORM objects to process

        Returns:
            List of lists of (gazetteer_name, identifier) tuples for each reference
        """
        if not references:
            return []

        # Step 1: Extract contexts for all references
        contexts = self._extract_contexts(references)

        # Step 2: Get all unique candidates across all references
        all_candidates = self._get_all_candidates(references)

        # Step 3: Generate location descriptions for all unique candidates
        unique_candidates = self._get_unique_candidates(all_candidates)
        candidate_descriptions = self._generate_descriptions(unique_candidates)

        # Step 4: Generate embeddings for contexts and candidate descriptions
        context_embeddings = self._generate_embeddings(contexts)
        candidate_embeddings = self._generate_embeddings(candidate_descriptions)

        # Step 5: Find best matches for each reference
        results = []
        for i, reference in enumerate(references):
            context_embedding = context_embeddings[i]
            reference_candidates = all_candidates[i]

            if not reference_candidates:
                results.append([])
                continue

            # Get embeddings for this reference's candidates
            ref_candidate_embeddings = []
            for candidate in reference_candidates:
                desc = self._get_description(candidate)
                embedding_idx = candidate_descriptions.index(desc)
                ref_candidate_embeddings.append(candidate_embeddings[embedding_idx])

            # Calculate similarities and find best match
            similarities = self._calculate_similarities(
                context_embedding, ref_candidate_embeddings
            )

            best_matches = self._select_best_matches(reference_candidates, similarities)

            results.append(best_matches)

        return results

    def _extract_contexts(self, references: List["Reference"]) -> List[str]:
        """
        Extract context around each reference, respecting model token limits.

        Args:
            references: List of Reference objects

        Returns:
            List of context strings for each reference
        """
        contexts = []
        max_seq_length = self.transformer.get_max_seq_length()
        # Reserve space for special tokens ([CLS] and [SEP] for BERT-like models)
        token_limit = max_seq_length - 2

        for reference in references:
            doc_text = reference.document.text
            ref_start = reference.start
            ref_end = reference.end

            # Check if entire document fits within token limit
            doc_tokens = len(self.tokenizer.tokenize(doc_text))
            if doc_tokens <= token_limit:
                contexts.append(doc_text)
                continue

            # Use spaCy to get sentence boundaries
            doc = self.nlp(doc_text)
            sentences = list(doc.sents)

            # Find the sentence containing the reference
            target_sentence = None
            for sent in sentences:
                if sent.start_char <= ref_start < sent.end_char:
                    target_sentence = sent
                    break

            # Get sentence index
            target_idx = sentences.index(target_sentence)
            context_sentences = [target_sentence]

            # Calculate tokens for target sentence
            tokens_count = len(self.tokenizer.tokenize(target_sentence.text))

            # Expand context bidirectionally while respecting token limit
            i, j = target_idx, target_idx

            while True:
                expanded = False

                # Try to add previous sentence
                if i > 0:
                    prev_sentence = sentences[i - 1]
                    prev_tokens = len(self.tokenizer.tokenize(prev_sentence.text))
                    if tokens_count + prev_tokens <= token_limit:
                        context_sentences.insert(0, prev_sentence)
                        tokens_count += prev_tokens
                        i -= 1
                        expanded = True

                # Try to add next sentence
                if j < len(sentences) - 1:
                    next_sentence = sentences[j + 1]
                    next_tokens = len(self.tokenizer.tokenize(next_sentence.text))
                    if tokens_count + next_tokens <= token_limit:
                        context_sentences.append(next_sentence)
                        tokens_count += next_tokens
                        j += 1
                        expanded = True

                if not expanded:
                    break

            # Combine sentences to form context
            context = " ".join(sent.text for sent in context_sentences)
            contexts.append(context)

        return contexts

    def _get_all_candidates(
        self, references: List["Reference"]
    ) -> List[List["Feature"]]:
        """
        Retrieve candidate features for all references from a gazetteer.

        Args:
            references: List of Reference objects

        Returns:
            List of candidate lists for each reference
        """
        all_candidates = []

        for reference in references:
            reference_candidates = []

            # Try exact match first
            candidates = self.gazetteer.search_exact(
                reference.text, limit=self.max_candidates
            )

            # If no exact matches, try partial matching
            if not candidates:
                candidates = self.gazetteer.search_partial(
                    reference.text, limit=self.max_candidates
                )

            # If still no matches, try fuzzy matching
            if not candidates:
                candidates = self.gazetteer.search_fuzzy(
                    reference.text, limit=self.max_candidates
                )

            reference_candidates.extend(candidates)

            all_candidates.append(reference_candidates)

        return all_candidates

    def _get_unique_candidates(
        self, all_candidates: List[List["Feature"]]
    ) -> List["Feature"]:
        """
        Extract unique candidates from all references to avoid duplicate processing.

        Args:
            all_candidates: List of candidate lists for each reference

        Returns:
            List of unique Feature objects
        """
        unique_candidates = {}

        for candidates in all_candidates:
            for candidate in candidates:
                # Use gazetteer_name + identifier_value as unique key
                key = f"{self.gazetteer_name}:{candidate.identifier_value}"
                if key not in unique_candidates:
                    unique_candidates[key] = candidate

        return list(unique_candidates.values())

    def _generate_descriptions(self, candidates: List["Feature"]) -> List[str]:
        """
        Generate textual descriptions for candidate locations.

        Args:
            candidates: List of Feature objects

        Returns:
            List of location description strings
        """
        descriptions = []

        for candidate in candidates:
            description = self._get_description(candidate)
            descriptions.append(description)

        return descriptions

    def _get_description(self, candidate: "Feature") -> str:
        """
        Generate a textual description for a single candidate location.

        Args:
            candidate: Feature object

        Returns:
            Location description string
        """
        # Check cache first
        cache_key = f"{self.gazetteer_name}:{candidate.identifier_value}"
        if cache_key in self.description_cache:
            return self.description_cache[cache_key]

        # Get location data
        location_data = candidate.data

        # Get attribute mappings for this gazetteer
        if self.gazetteer_name not in self.GAZETTEER_ATTRIBUTE_MAP:
            raise ValueError(
                f"Gazetteer '{self.gazetteer_name}' is not configured in GAZETTEER_ATTRIBUTE_MAP"
            )

        attr_map = self.GAZETTEER_ATTRIBUTE_MAP[self.gazetteer_name]

        # Extract attributes
        feature_name = location_data.get(attr_map["name"])
        feature_type = location_data.get(attr_map["type"])

        # Build description components
        description_parts = []

        # Add feature name if available
        if feature_name:
            description_parts.append(feature_name)

        # Add feature type in brackets if available
        if feature_type:
            description_parts.append(f"({feature_type})")

        # Build hierarchical context from admin levels
        admin_levels = []
        for level in ["level3", "level2", "level1"]:
            if level in attr_map:
                admin_value = location_data.get(attr_map[level])
                if admin_value:
                    admin_levels.append(admin_value)

        # Combine description parts
        if admin_levels:
            description_parts.append("in")
            description_parts.append(", ".join(admin_levels))

        description = " ".join(description_parts).strip()

        # Cache the result
        self.description_cache[cache_key] = description

        return description

    def _generate_embeddings(self, texts: List[str]) -> List[torch.Tensor]:
        """
        Generate embeddings for a list of texts using SentenceTransformer.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding tensors
        """
        if not texts:
            return []

        # Check cache for existing embeddings
        cached_embeddings = []
        texts_to_embed = []
        cache_indices = []

        for i, text in enumerate(texts):
            if text in self.embedding_cache:
                cached_embeddings.append((i, self.embedding_cache[text]))
            else:
                texts_to_embed.append(text)
                cache_indices.append(i)

        # Generate embeddings for uncached texts
        new_embeddings = []
        if texts_to_embed:
            embeddings = self.transformer.encode(
                texts_to_embed, convert_to_tensor=True, batch_size=32
            )

            # Cache new embeddings
            for text, embedding in zip(texts_to_embed, embeddings):
                self.embedding_cache[text] = embedding
                new_embeddings.append(embedding)

        # Combine cached and new embeddings in correct order
        result_embeddings = [None] * len(texts)

        # Place cached embeddings
        for idx, embedding in cached_embeddings:
            result_embeddings[idx] = embedding

        # Place new embeddings
        for cache_idx, embedding in zip(cache_indices, new_embeddings):
            result_embeddings[cache_idx] = embedding

        return result_embeddings

    def _calculate_similarities(
        self, context_embedding: torch.Tensor, candidate_embeddings: List[torch.Tensor]
    ) -> List[float]:
        """
        Calculate cosine similarities between context and candidate embeddings.

        Args:
            context_embedding: Embedding tensor for the reference context
            candidate_embeddings: List of embedding tensors for candidates

        Returns:
            List of similarity scores
        """
        if not candidate_embeddings:
            return []

        # Stack candidate embeddings
        candidate_tensor = torch.stack(candidate_embeddings)

        # Calculate cosine similarities
        similarities = torch.nn.functional.cosine_similarity(
            context_embedding.unsqueeze(0), candidate_tensor, dim=1
        )

        return similarities.tolist()

    def _select_best_matches(
        self, candidates: List["Feature"], similarities: List[float]
    ) -> List[Tuple[str, str]]:
        """
        Select the best matching candidates based on similarity scores.

        Args:
            candidates: List of candidate Feature objects
            similarities: List of similarity scores corresponding to candidates

        Returns:
            List of (gazetteer_name, identifier) tuples for best matches
        """
        if not candidates or not similarities:
            return []

        # Find candidates above threshold
        valid_matches = [
            (candidate, similarity)
            for candidate, similarity in zip(candidates, similarities)
            if similarity >= self.similarity_threshold
        ]

        if not valid_matches:
            return []

        # Sort by similarity score (descending)
        valid_matches.sort(key=lambda x: x[1], reverse=True)

        # Return the best match (could be extended to return multiple matches)
        best_candidate, _ = valid_matches[0]
        return [(self.gazetteer_name, best_candidate.identifier_value)]
