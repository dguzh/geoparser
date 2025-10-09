import typing as t
from pathlib import Path
from typing import Dict, List, Tuple, Union

import spacy
import torch
from datasets import Dataset
from sentence_transformers import SentenceTransformer, SentenceTransformerTrainer
from sentence_transformers.losses import ContrastiveLoss
from sentence_transformers.training_args import SentenceTransformerTrainingArguments
from transformers import AutoTokenizer

from geoparser.gazetteer.gazetteer import Gazetteer
from geoparser.modules.resolvers import Resolver

if t.TYPE_CHECKING:
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
        self.context_embeddings: Dict[str, torch.Tensor] = {}  # context -> embedding
        self.candidate_embeddings: Dict[int, torch.Tensor] = (
            {}
        )  # feature_id -> embedding

    def predict_referents(
        self, texts: t.List[str], references: t.List[t.List[t.Tuple[int, int]]]
    ) -> t.List[t.List[t.Union[t.Tuple[str, str], None]]]:
        """
        Predict referents for multiple references using iterative candidate generation.

        Uses a search strategy that starts with restrictive search methods and
        progressively expands to less restrictive ones, stopping when candidates
        with sufficient similarity are found.

        Args:
            texts: List of document text strings
            references: List of lists of tuples containing (start, end) positions of references

        Returns:
            List of lists where each element is either:
            - A tuple (gazetteer_name, identifier) for a successfully resolved reference
            - None if prediction is not available for that specific reference
        """
        # Check if there are any texts to process
        if not texts:
            return []

        # Step 1: Extract contexts for all references
        contexts = self._extract_contexts(texts, references)

        # Step 2: Embed all contexts
        self._embed_contexts(contexts)

        # Initialize tracking structures (nested by document)
        results = [[None for _ in doc_refs] for doc_refs in references]
        candidates = [[[] for _ in doc_refs] for doc_refs in references]

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

                # Step 3: Gather candidates for unresolved references
                self._gather_candidates(
                    texts, references, candidates, results, method, ranks
                )

                # Step 4: Embed new candidates
                self._embed_candidates(candidates, results)

                # Step 5: Evaluate candidates and update results
                self._evaluate_candidates(
                    contexts, candidates, results, self.min_similarity
                )

                # If all references resolved, we can stop
                if all(
                    all(r is not None for r in doc_results) for doc_results in results
                ):
                    break

            # If all references resolved, we can stop
            if all(all(r is not None for r in doc_results) for doc_results in results):
                break

        # Handle remaining unresolved references by selecting best candidates (min_similarity=0.0)
        self._evaluate_candidates(contexts, candidates, results)

        # Ensure we have a result for every reference
        results = [
            [
                result if result is not None else (self.gazetteer_name, "")
                for result in doc_results
            ]
            for doc_results in results
        ]

        return results

    def _extract_contexts(
        self, texts: List[str], references: List[List[Tuple[int, int]]]
    ) -> List[List[str]]:
        """
        Extract contexts for all references.

        Args:
            texts: List of document text strings
            references: List of lists of tuples containing (start, end) positions of references

        Returns:
            List of lists of context strings, matching the structure of references
        """
        contexts = []
        for text, doc_references in zip(texts, references):
            doc_contexts = []
            for start, end in doc_references:
                context = self._extract_context(text, start, end)
                doc_contexts.append(context)
            contexts.append(doc_contexts)
        return contexts

    def _embed_contexts(self, contexts: List[List[str]]) -> None:
        """
        Generate embeddings for contexts, avoiding duplicate work.

        Args:
            contexts: List of lists of context strings
        """
        # Collect unique contexts that need encoding
        contexts_to_encode = set()
        for doc_contexts in contexts:
            for context in doc_contexts:
                # Only encode contexts we haven't seen before
                if context not in self.context_embeddings:
                    contexts_to_encode.add(context)

        # Encode unique contexts in batch
        if contexts_to_encode:
            unique_contexts = list(contexts_to_encode)
            embeddings = self.transformer.encode(
                unique_contexts,
                convert_to_tensor=True,
                batch_size=32,
                show_progress_bar=True,
            )

            # Store embeddings in cache with context as key
            for context, embedding in zip(unique_contexts, embeddings):
                self.context_embeddings[context] = embedding

    def _gather_candidates(
        self,
        texts: List[str],
        references: List[List[Tuple[int, int]]],
        candidates: List[List[List["Feature"]]],
        results: List[List[Tuple[str, str]]],
        method: str,
        ranks: int,
    ) -> None:
        """
        Gather candidates for unresolved references using the specified search method.

        Args:
            texts: List of document text strings
            references: List of lists of tuples containing (start, end) positions of references
            candidates: Nested list of candidate lists for each reference (modified in-place)
            results: Nested list of current results to determine which references need candidates
            method: Search method to use
            ranks: Number of rank groups to include
        """
        for doc_idx, (text, doc_references, doc_candidates, doc_results) in enumerate(
            zip(texts, references, candidates, results)
        ):
            for ref_idx, ((start, end), result) in enumerate(
                zip(doc_references, doc_results)
            ):
                # Skip already resolved references
                if result is not None:
                    continue

                # Search for new candidates and merge with existing ones, avoiding duplicates
                reference_text = text[start:end]
                new_candidates = self.gazetteer.search(
                    reference_text, method, ranks=ranks
                )
                existing_ids = {c.id for c in doc_candidates[ref_idx]}
                for candidate in new_candidates:
                    if candidate.id not in existing_ids:
                        doc_candidates[ref_idx].append(candidate)

    def _embed_candidates(
        self,
        candidates: List[List[List["Feature"]]],
        results: List[List[Tuple[str, str]]],
    ) -> None:
        """
        Generate embeddings for candidates that need to be processed.

        Args:
            candidates: Nested list of candidate lists for each reference
            results: Nested list of current results to determine which candidates need embedding
        """
        # Collect unique candidates that need embedding
        candidates_to_embed = {}  # Use dict to avoid duplicates: id -> candidate

        for doc_candidates, doc_results in zip(candidates, results):
            for candidate_list, result in zip(doc_candidates, doc_results):
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
        contexts: List[List[str]],
        candidates: List[List[List["Feature"]]],
        results: List[List[Tuple[str, str]]],
        min_similarity: float = 0.0,
    ) -> None:
        """
        Evaluate candidates against reference contexts and update results.

        Args:
            contexts: List of lists of context strings
            candidates: Nested list of candidate lists for each reference
            results: Nested list of current results (modified in-place)
            min_similarity: Minimum similarity threshold (default: 0.0)
        """
        for doc_idx, (doc_contexts, doc_candidates, doc_results) in enumerate(
            zip(contexts, candidates, results)
        ):
            for ref_idx, (context, candidate_list, result) in enumerate(
                zip(doc_contexts, doc_candidates, doc_results)
            ):
                # Skip already resolved references
                if result is not None:
                    continue

                # Skip if no candidates
                if not candidate_list:
                    continue

                # Get reference context embedding using context as key
                context_embedding = self.context_embeddings[context]

                # Get candidate embeddings
                candidate_embeddings = [
                    self.candidate_embeddings[candidate.id]
                    for candidate in candidate_list
                ]

                # Calculate similarities
                similarities = self._calculate_similarities(
                    context_embedding, candidate_embeddings
                )

                # Find best candidate
                best_idx = max(range(len(similarities)), key=lambda j: similarities[j])
                best_similarity = similarities[best_idx]
                best_candidate = candidate_list[best_idx]

                # Check if similarity meets threshold
                if best_similarity >= min_similarity:
                    doc_results[ref_idx] = (
                        self.gazetteer_name,
                        best_candidate.identifier_value,
                    )

    def _extract_context(self, text: str, start: int, end: int) -> str:
        """
        Extract context around a single reference, respecting model token limits.

        Args:
            text: Full document text
            start: Start position of the reference
            end: End position of the reference

        Returns:
            Context string for the reference
        """
        max_seq_length = self.transformer.get_max_seq_length()
        # Reserve space for special tokens ([CLS] and [SEP] for BERT-like models)
        token_limit = max_seq_length - 2

        # Check if entire document fits within token limit
        doc_tokens = len(self.tokenizer.tokenize(text))
        if doc_tokens <= token_limit:
            return text

        # Use spaCy to get sentence boundaries
        doc = self.nlp(text)
        sentences = list(doc.sents)

        # Find the sentence containing the reference
        target_sentence = None
        for sent in sentences:
            if sent.start_char <= start < sent.end_char:
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
        return context

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
        context_embedding: torch.Tensor,
        candidate_embeddings: List[torch.Tensor],
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

    def fit(
        self,
        texts: List[str],
        references: List[List[Tuple[int, int]]],
        referents: List[List[Tuple[str, str]]],
        output_path: Union[str, Path],
        epochs: int = 1,
        batch_size: int = 8,
        learning_rate: float = 2e-5,
        warmup_ratio: float = 0.1,
        save_strategy: str = "epoch",
    ) -> None:
        """
        Fine-tune the SentenceTransformer model using references and their resolved referents as training data.

        This method gathers all references that have been resolved (i.e., have referents), extracts
        their contexts and all candidate descriptions, and uses them to create positive and negative
        training examples for fine-tuning the underlying SentenceTransformer model using ContrastiveLoss.

        Args:
            texts: List of document text strings
            references: List of lists of (start, end) position tuples
            referents: List of lists of (gazetteer_name, identifier) tuples
            output_path: Directory path to save the fine-tuned model
            epochs: Number of training epochs (default: 1)
            batch_size: Training batch size (default: 8)
            learning_rate: Learning rate for training (default: 2e-5)
            warmup_ratio: Warmup ratio for learning rate scheduler (default: 0.1)
            save_strategy: When to save the model during training (default: "epoch")

        Raises:
            ValueError: If no training examples can be created from the provided documents
        """
        print("Preparing training data from referent annotations...")

        # Step 1: Gather training data from resolved references
        training_data = self._prepare_training_data(texts, references, referents)

        if not training_data["sentence1"] or len(training_data["sentence1"]) == 0:
            raise ValueError(
                "No training examples found. Ensure documents contain references with referent annotations."
            )

        print(f"Created {len(training_data['sentence1'])} training examples")

        # Step 2: Create training dataset
        train_dataset = Dataset.from_dict(training_data)

        # Step 3: Setup training loss
        train_loss = ContrastiveLoss(self.transformer)

        # Step 4: Configure training arguments
        training_args = SentenceTransformerTrainingArguments(
            output_dir=str(output_path),
            num_train_epochs=epochs,
            per_device_train_batch_size=batch_size,
            learning_rate=learning_rate,
            warmup_ratio=warmup_ratio,
            save_strategy=save_strategy,
            logging_strategy="steps",
            logging_steps=max(1, len(training_data["sentence1"]) // (batch_size * 10)),
            eval_strategy="no",  # No evaluation for now
            save_total_limit=2,  # Keep only 2 checkpoints
            load_best_model_at_end=False,
        )

        # Step 5: Create trainer
        trainer = SentenceTransformerTrainer(
            model=self.transformer,
            args=training_args,
            train_dataset=train_dataset,
            loss=train_loss,
        )

        print("Starting model fine-tuning...")

        # Step 6: Train the model
        trainer.train()

        # Step 7: Save the final model
        self.transformer.save_pretrained(str(output_path))

        print(f"Model fine-tuning completed and saved to: {output_path}")

    def _prepare_training_data(
        self,
        texts: List[str],
        references: List[List[Tuple[int, int]]],
        referents: List[List[Tuple[str, str]]],
    ) -> Dict[str, List]:
        """
        Prepare training data from documents with resolved references.

        This method extracts all references that have been resolved (have referents),
        gets their contexts and all candidate descriptions to create both positive
        and negative training examples for ContrastiveLoss.

        Args:
            texts: List of document text strings
            references: List of lists of (start, end) position tuples
            referents: List of lists of (gazetteer_name, identifier) tuples

        Returns:
            Dictionary with 'sentence1', 'sentence2', and 'label' lists for training
        """
        sentence1_texts = []  # contexts
        sentence2_texts = []  # candidate descriptions
        labels = []  # 1 for positive, 0 for negative

        for text, doc_references, doc_referents in zip(texts, references, referents):
            for (start, end), (gazetteer_name, identifier) in zip(
                doc_references, doc_referents
            ):
                # Extract context for this reference
                context = self._extract_context(text, start, end)

                # Get all candidates for this reference text to create negative examples
                reference_text = text[start:end]
                candidates = self.gazetteer.search(reference_text)

                for candidate in candidates:
                    # Generate description for this candidate
                    description = self._generate_description(candidate)

                    # Determine if this is a positive or negative example
                    label = 1 if candidate.identifier_value == identifier else 0

                    # Add as training example
                    sentence1_texts.append(context)
                    sentence2_texts.append(description)
                    labels.append(label)

        return {
            "sentence1": sentence1_texts,
            "sentence2": sentence2_texts,
            "label": labels,
        }
