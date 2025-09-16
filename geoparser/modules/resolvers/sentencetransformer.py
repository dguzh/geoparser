import typing as t
from typing import Dict, List, Tuple

import spacy
import torch
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer

from geoparser.gazetteer.gazetteer import Gazetteer
from geoparser.modules.resolvers import Resolver

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
        self.reference_embeddings: Dict[int, torch.Tensor] = (
            {}
        )  # reference_id -> embedding
        self.candidate_embeddings: Dict[int, torch.Tensor] = (
            {}
        )  # feature_id -> embedding

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

        # Step 1: Embed all references
        self._embed_references(references)

        # Initialize tracking structures
        results = [None] * len(references)
        candidates = [[]] * len(references)

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

                # Step 2: Gather candidates for unresolved references
                self._gather_candidates(references, candidates, results, method, ranks)

                # Step 3: Embed new candidates
                self._embed_candidates(candidates, results)

                # Step 4: Evaluate candidates and update results
                self._evaluate_candidates(
                    references, candidates, results, self.min_similarity
                )

                # If all references resolved, we can stop
                if all(result is not None for result in results):
                    break

            # If all references resolved, we can stop
            if all(result is not None for result in results):
                break

        # Handle remaining unresolved references by selecting best candidates (min_similarity=0.0)
        self._evaluate_candidates(references, candidates, results)

        # Ensure we have a result for every reference
        results = [
            result if result is not None else (self.gazetteer_name, "")
            for result in results
        ]

        return results

    def _embed_references(self, references: List["Reference"]) -> None:
        """
        Extract contexts and generate embeddings for references, avoiding duplicate work.

        Args:
            references: List of Reference objects to embed
        """
        if not references:
            return

        # Extract contexts for all references
        contexts = self._extract_contexts(references)

        # Group references by identical context text to avoid duplicate encoding
        context_to_refs = {}
        for reference, context in zip(references, contexts):
            if context not in context_to_refs:
                context_to_refs[context] = []
            context_to_refs[context].append(reference)

        # Get unique contexts and encode them in batch
        unique_contexts = list(context_to_refs.keys())
        if unique_contexts:
            embeddings = self.transformer.encode(
                unique_contexts,
                convert_to_tensor=True,
                batch_size=32,
                show_progress_bar=True,
            )

            # Store embeddings for all references with the same context
            for context, embedding in zip(unique_contexts, embeddings):
                for reference in context_to_refs[context]:
                    self.reference_embeddings[reference.id] = embedding

    def _gather_candidates(
        self,
        references: List["Reference"],
        candidates: List[List["Feature"]],
        results: List[Tuple[str, str]],
        method: str,
        ranks: int,
    ) -> None:
        """
        Gather candidates for unresolved references using the specified search method.

        Args:
            references: List of all references
            candidates: List of candidate lists for each reference (modified in-place)
            results: List of current results to determine which references need candidates
            method: Search method to use
            ranks: Number of rank groups to include
        """
        for i, (reference, result) in enumerate(zip(references, results)):
            # Skip already resolved references
            if result is not None:
                continue

            # Search for new candidates and merge with existing ones, avoiding duplicates
            new_candidates = self.gazetteer.search(reference.text, method, ranks=ranks)
            existing_ids = {c.id for c in candidates[i]}
            for candidate in new_candidates:
                if candidate.id not in existing_ids:
                    candidates[i].append(candidate)

    def _embed_candidates(
        self, candidates: List[List["Feature"]], results: List[Tuple[str, str]]
    ) -> None:
        """
        Generate embeddings for candidates that need to be processed.

        Args:
            candidates: List of candidate lists for each reference
            results: List of current results to determine which candidates need embedding
        """
        # Collect unique candidates that need embedding
        candidates_to_embed = {}  # Use dict to avoid duplicates: id -> candidate

        for i, (candidate_list, result) in enumerate(zip(candidates, results)):
            # Skip already resolved references
            if result is not None:
                continue

            # Add candidates that don't have embeddings yet
            for candidate in candidate_list:
                if candidate.id not in self.candidate_embeddings:
                    candidates_to_embed[candidate.id] = candidate

        if not candidates_to_embed:
            return

        # Convert to list for consistent ordering
        candidates_list = list(candidates_to_embed.values())

        # Generate descriptions for candidates
        descriptions = [
            self._generate_description(candidate) for candidate in candidates_list
        ]

        # Generate embeddings in batch
        if descriptions:
            embeddings = self.transformer.encode(
                descriptions,
                convert_to_tensor=True,
                batch_size=32,
                show_progress_bar=True,
            )

            # Store embeddings in cache
            for candidate, embedding in zip(candidates_list, embeddings):
                self.candidate_embeddings[candidate.id] = embedding

    def _evaluate_candidates(
        self,
        references: List["Reference"],
        candidates: List[List["Feature"]],
        results: List[Tuple[str, str]],
        min_similarity: float = 0.0,
    ) -> None:
        """
        Evaluate candidates against reference contexts and update results.

        Args:
            references: List of all references
            candidates: List of candidate lists for each reference
            results: List of current results (modified in-place)
            min_similarity: Minimum similarity threshold (default: 0.0)
        """
        for i, (reference, candidate_list, result) in enumerate(
            zip(references, candidates, results)
        ):
            # Skip already resolved references
            if result is not None:
                continue

            # Skip if no candidates
            if not candidate_list:
                continue

            # Get reference embedding
            reference_embedding = self.reference_embeddings[reference.id]

            # Get candidate embeddings
            candidate_embeddings = [
                self.candidate_embeddings[candidate.id] for candidate in candidate_list
            ]

            # Calculate similarities
            similarities = self._calculate_similarities(
                reference_embedding, candidate_embeddings
            )

            # Find best candidate
            best_idx = max(range(len(similarities)), key=lambda j: similarities[j])
            best_similarity = similarities[best_idx]
            best_candidate = candidate_list[best_idx]

            # Check if similarity meets threshold
            if best_similarity >= min_similarity:
                results[i] = (self.gazetteer_name, best_candidate.identifier_value)

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
            reference_start = reference.start
            reference_end = reference.end

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
                if sent.start_char <= reference_start < sent.end_char:
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

        return description

    def _calculate_similarities(
        self,
        reference_embedding: torch.Tensor,
        candidate_embeddings: List[torch.Tensor],
    ) -> List[float]:
        """
        Calculate cosine similarities between context and candidate embeddings.

        Args:
            reference_embedding: Embedding tensor for the reference context
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
            reference_embedding.unsqueeze(0), candidate_tensor, dim=1
        )

        return similarities.tolist()
