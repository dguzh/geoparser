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
        min_similarity: float = 0.7,
        max_iter: int = 3,
    ):
        """
        Initialize the SentenceTransformerResolver.

        Args:
            model_name: HuggingFace model name for SentenceTransformer
            gazetteer_name: Name of the gazetteer to search
            min_similarity: Minimum similarity threshold to stop candidate generation
            max_iter: Maximum number of iterations through search methods with increasing ranks
        """
        # Initialize parent with the parameters
        super().__init__(
            model_name=model_name,
            gazetteer_name=gazetteer_name,
            min_similarity=min_similarity,
            max_iter=max_iter,
        )

        # Store instance attributes directly from parameters
        self.model_name = model_name
        self.gazetteer_name = gazetteer_name
        self.min_similarity = min_similarity
        self.max_iter = max_iter

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
        self, references: t.List["Reference"]
    ) -> t.List[t.Tuple[str, str]]:
        """
        Predict referents for multiple references using iterative candidate generation.

        Uses a search strategy that starts with restrictive search methods and
        progressively expands to less restrictive ones, stopping when candidates
        with sufficient similarity are found.

        Args:
            references: List of Reference ORM objects to process

        Returns:
            List of (gazetteer_name, identifier) tuples - each reference gets exactly one referent
        """
        # Check if there are any references to process
        if not references:
            return []

        # Extract contexts and generate embeddings for all references
        context_texts = self._extract_contexts(references)
        context_embeddings = self._generate_embeddings(context_texts)

        # Initialize tracking structures
        results = [None] * len(references)
        best_candidates = [None] * len(references)
        best_similarities = [0.0] * len(references)

        # Define search methods in order of preference
        search_methods = [
            "exact",
            "phrase",
            "substring",
            "permuted",
            "partial",
            "fuzzy",
        ]

        # Iterative search strategy with increasing ranks
        for ranks in range(1, self.max_iter + 1):

            for method in search_methods:
                # Skip exact method for ranks > 1
                if method == "exact" and ranks > 1:
                    continue

                # Search for candidates for all unresolved references
                all_candidates = self._search_candidates(
                    method, ranks, references, results
                )

                if not all_candidates:
                    break  # All references resolved

                # Evaluate candidates and update tracking structures
                self._evaluate_candidates(
                    all_candidates,
                    context_embeddings,
                    results,
                    best_candidates,
                    best_similarities,
                )

                # If all references resolved, we can stop
                if all(result is not None for result in results):
                    break

            # If all references resolved, we can stop
            if all(result is not None for result in results):
                break

        # For any remaining unresolved references, use the best candidate found
        for i, result in enumerate(results):
            if result is None and best_candidates[i] is not None:
                results[i] = (self.gazetteer_name, best_candidates[i].identifier_value)

        # Ensure we have a result for every reference using list comprehension
        results = [
            result if result is not None else (self.gazetteer_name, "")
            for result in results
        ]

        return results

    def _search_candidates(
        self,
        method: str,
        ranks: int,
        references: List["Reference"],
        results: List[Tuple[str, str]],
    ) -> List[Tuple[int, List["Feature"]]]:
        """
        Search for candidates for all unresolved references using a specific method.

        Args:
            method: Name of the search method to use
            ranks: Number of rank groups to include for ranked methods
            references: List of all references being processed
            results: List of current results to determine which references are unresolved

        Returns:
            List of tuples containing (reference_index, candidates_list)
        """
        # Get unresolved references for this round
        unresolved_indices = [i for i, result in enumerate(results) if result is None]
        if not unresolved_indices:
            return []

        # Search for candidates for all unresolved references
        all_candidates = []
        for idx in unresolved_indices:
            reference = references[idx]
            candidates = self.gazetteer.search(reference.text, method, ranks=ranks)
            all_candidates.append((idx, candidates))

        return all_candidates

    def _evaluate_candidates(
        self,
        all_candidates: List[Tuple[int, List["Feature"]]],
        context_embeddings: List[torch.Tensor],
        results: List[Tuple[str, str]],
        best_candidates: List["Feature"],
        best_similarities: List[float],
    ) -> None:
        """
        Evaluate candidates and update tracking structures.

        Args:
            all_candidates: List of (reference_index, candidates) tuples
            context_embeddings: Embeddings for reference contexts
            results: Results list to update when references are resolved
            best_candidates: List to track best candidates found so far
            best_similarities: List to track best similarities found so far
        """
        # Evaluate and compare candidates for each unresolved reference
        for idx, candidates in all_candidates:
            if not candidates:
                continue

            # Find the best candidate for the context
            context_embedding = context_embeddings[idx]
            best_candidate, best_similarity = self._find_best_candidate(
                context_embedding, candidates
            )

            # Update best candidate found so far
            if best_similarity > best_similarities[idx]:
                best_candidates[idx] = best_candidate
                best_similarities[idx] = best_similarity

            # Check if similarity meets threshold
            if best_similarity >= self.min_similarity:
                results[idx] = (self.gazetteer_name, best_candidate.identifier_value)

    def _find_best_candidate(
        self, context_embedding: torch.Tensor, candidates: List["Feature"]
    ) -> Tuple["Feature", float]:
        """
        Find the best candidate match against a context embedding.

        Args:
            context_embedding: Embedding tensor for the reference context
            candidates: List of candidate features to evaluate

        Returns:
            Tuple of (best_candidate, best_similarity)
        """
        if not candidates:
            return None, 0.0

        # Get descriptions and embeddings for candidates
        candidate_descriptions = [
            self._generate_description(candidate) for candidate in candidates
        ]
        candidate_embeddings = self._generate_embeddings(candidate_descriptions)

        # Calculate similarities
        similarities = self._calculate_similarities(
            context_embedding, candidate_embeddings
        )

        # Find best match
        best_idx = max(range(len(similarities)), key=lambda i: similarities[i])
        return candidates[best_idx], similarities[best_idx]

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

    def _generate_description(self, candidate: "Feature") -> str:
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
        missing_texts = []
        missing_indices = []

        for i, text in enumerate(texts):
            if text in self.embedding_cache:
                cached_embeddings.append((i, self.embedding_cache[text]))
            else:
                missing_texts.append(text)
                missing_indices.append(i)

        # Generate embeddings for uncached texts
        if missing_texts:
            embeddings = self.transformer.encode(
                missing_texts, convert_to_tensor=True, batch_size=32
            )

            # Cache new embeddings
            for text, embedding in zip(missing_texts, embeddings):
                self.embedding_cache[text] = embedding

        # Combine cached and new embeddings in correct order
        result_embeddings = [None] * len(texts)

        # Place cached embeddings
        for idx, embedding in cached_embeddings:
            result_embeddings[idx] = embedding

        # Place new embeddings
        if missing_texts:
            for idx, embedding in zip(missing_indices, embeddings):
                result_embeddings[idx] = embedding

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
