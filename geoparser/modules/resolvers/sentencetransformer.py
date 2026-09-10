import typing as t
from pathlib import Path

import spacy
import spacy.tokens
import torch
from datasets import Dataset
from sentence_transformers import SentenceTransformer, SentenceTransformerTrainer
from sentence_transformers.sentence_transformer.losses import ContrastiveLoss
from sentence_transformers.sentence_transformer.training_args import (
    SentenceTransformerTrainingArguments,
)
from transformers import AutoTokenizer, PreTrainedTokenizerBase, logging

from geoparser.gazetteer.gazetteer import Gazetteer
from geoparser.modules.resolvers import Resolver

if t.TYPE_CHECKING:
    from geoparser.gazetteer.feature import Feature

# Suppress transformers tokenizer token length warnings
logging.set_verbosity_error()


class SentenceTransformerResolver(Resolver):
    """
    A resolver that uses SentenceTransformer to map reference contexts to gazetteer candidates.

    This resolver extracts contextual information around each reference, generates embeddings
    for the context, retrieves candidate features from the gazetteer, generates location
    descriptions and embeddings for candidates, and finds the best match using cosine similarity.
    """

    NAME = "SentenceTransformerResolver"

    # Search methods in order of preference, from most to least restrictive.
    SEARCH_METHODS: t.ClassVar[tuple[str, ...]] = (
        "exact",
        "phrase",
        "partial",
        "fuzzy",
    )

    # Gazetteer-specific attribute mappings for location descriptions
    GAZETTEER_ATTRIBUTE_MAP: t.ClassVar[dict[str, dict[str, str]]] = {
        "geonames": {
            "name": "name",
            "type": "feature_name",
            "level1": "country_name",
            "level2": "admin1_name",
            "level3": "admin2_name",
        },
        "geonames-cities": {
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
        min_similarity: float = 0.6,
        max_tiers: int = 3,
        attribute_map: dict | None = None,
    ):
        """
        Initialize the SentenceTransformerResolver.

        Args:
            model_name: HuggingFace model name for SentenceTransformer
            gazetteer_name: Name of the gazetteer to search
            min_similarity: Minimum similarity threshold to stop candidate generation
            max_tiers: Maximum number of tiers to expand through search methods
            attribute_map: Optional custom attribute mapping for gazetteer.
                          If None, will look up gazetteer_name in GAZETTEER_ATTRIBUTE_MAP.
                          If provided, will be used directly.
                          Should have keys: "name", "type", "level1", "level2", "level3"
        """
        # Initialize parent with the parameters
        super().__init__(
            model_name=model_name,
            gazetteer_name=gazetteer_name,
            min_similarity=min_similarity,
            max_tiers=max_tiers,
            attribute_map=attribute_map,
        )

        # Store instance attributes directly from parameters
        self.model_name = model_name
        self.gazetteer_name = gazetteer_name
        self.min_similarity = min_similarity
        self.max_tiers = max_tiers

        # Validate and set attribute map
        self.attribute_map = self._validate_and_set_attribute_map(
            gazetteer_name, attribute_map
        )

        # Initialize gazetteer first, so that a missing one is reported before
        # any time is spent loading models
        self.gazetteer = Gazetteer(gazetteer_name)

        # Initialize transformer and tokenizer
        self.transformer = SentenceTransformer(model_name)
        # Annotated explicitly: AutoTokenizer's return union includes backend
        # types (and None) that do not carry .tokenize, which is all this class
        # uses. Narrowing here types the four call sites correctly; from_pretrained
        # does not actually return None for a resolvable model name.
        self.tokenizer: PreTrainedTokenizerBase = AutoTokenizer.from_pretrained(  # ty: ignore[invalid-assignment]
            model_name
        )

        # Initialize spaCy model for sentence splitting
        self.nlp = self._load_spacy_model("xx_sent_ud_sm")

        # Caches for document processing to avoid recomputation
        self.doc_tokens: dict[str, int] = {}  # text -> token count
        self.doc_objects: dict[str, spacy.tokens.Doc] = {}  # text -> spaCy doc object

        # Caches for embeddings to avoid recomputation
        self.context_embeddings: dict[str, torch.Tensor] = {}  # context -> embedding
        self.candidate_embeddings: dict[
            int, torch.Tensor
        ] = {}  # feature_id -> embedding

    def _validate_and_set_attribute_map(
        self, gazetteer_name: str, attribute_map: dict | None = None
    ) -> dict:
        """
        Validate and set the attribute map for the gazetteer.

        Args:
            gazetteer_name: Name of the gazetteer
            attribute_map: Optional custom attribute mapping

        Returns:
            The validated attribute map dictionary

        Raises:
            ValueError: If gazetteer is not configured and no custom map is provided
        """
        if attribute_map is None:
            # Look up in GAZETTEER_ATTRIBUTE_MAP
            if gazetteer_name not in self.GAZETTEER_ATTRIBUTE_MAP:
                raise ValueError(
                    f"Gazetteer '{gazetteer_name}' is not configured in GAZETTEER_ATTRIBUTE_MAP. "
                    f"Please provide a custom attribute_map parameter."
                )
            return self.GAZETTEER_ATTRIBUTE_MAP[gazetteer_name]
        else:
            return attribute_map

    def _load_spacy_model(self, model_name: str) -> spacy.language.Language:
        """
        Load a spaCy model, downloading it if necessary.

        Args:
            model_name: Name of the spaCy model to load

        Returns:
            Loaded spaCy Language model
        """
        try:
            nlp = spacy.load(model_name)
        except OSError:
            # Model not found, download it
            print(f"Downloading spaCy model '{model_name}'...")
            spacy.cli.download(model_name)
            nlp = spacy.load(model_name)
        return nlp

    def predict(
        self, texts: list[str], references: list[list[tuple[int, int]]]
    ) -> list[list[tuple[str, str] | None]]:
        """
        Predict referents for multiple references using iterative candidate generation.

        Uses a search strategy that starts with restrictive search methods and
        progressively expands to less restrictive ones, stopping when candidates
        with sufficient similarity are found.

        Args:
            texts: List of document text strings
            references: List of lists of tuples containing (start, end) positions of references

        Returns:
            A list of lists where each inner list corresponds to referents for references in one
            document. Each element is either a tuple (gazetteer_name, identifier) for a
            successfully resolved reference, or None if prediction is not available for that
            specific reference.
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

        # Iterative search strategy with increasing tiers
        for tiers in range(1, self.max_tiers + 1):
            self._search_tier(texts, references, contexts, candidates, results, tiers)

            # If all references resolved, we can stop
            if self._all_resolved(results):
                break

        return results

    def _search_tier(
        self,
        texts: list[str],
        references: list[list[tuple[int, int]]],
        contexts: list[list[str]],
        candidates: list[list[list["Feature"]]],
        results: list[list[tuple[str, str] | None]],
        tiers: int,
    ) -> None:
        """
        Try each search method at one tier, stopping early once all are resolved.

        Args:
            texts: Document texts
            references: Per-document reference spans
            contexts: Per-reference context strings
            candidates: Per-reference candidate features, extended in place
            results: Per-reference referents, filled in place
            tiers: How far to expand the search on this pass
        """
        for method in self.SEARCH_METHODS:
            # The exact method cannot yield anything new once the search widens
            if method == "exact" and tiers > 1:
                continue

            self._search_once(
                texts, references, contexts, candidates, results, method, tiers
            )

            if self._all_resolved(results):
                break

    @staticmethod
    def _all_resolved(
        results: list[list[tuple[str, str] | None]],
    ) -> bool:
        """
        Whether every reference in every document has been resolved.

        Args:
            results: Per-document lists of referents, with None where a
                     reference is still unresolved

        Returns:
            True when no None remains
        """
        return all(all(r is not None for r in doc_results) for doc_results in results)

    def _search_once(
        self,
        texts: list[str],
        references: list[list[tuple[int, int]]],
        contexts: list[list[str]],
        candidates: list[list[list["Feature"]]],
        results: list[list[tuple[str, str] | None]],
        method: str,
        tiers: int,
    ) -> None:
        """
        Run one gather/embed/evaluate pass, updating candidates and results.

        Args:
            texts: Document texts
            references: Per-document reference spans
            contexts: Per-reference context strings
            candidates: Per-reference candidate features, extended in place
            results: Per-reference referents, filled in place
            method: Gazetteer search method for this pass
            tiers: How far to expand the search for this pass
        """
        self._gather_candidates(texts, references, candidates, results, method, tiers)
        self._embed_candidates(candidates, results)
        self._evaluate_candidates(contexts, candidates, results, self.min_similarity)

    def _extract_contexts(
        self, texts: list[str], references: list[list[tuple[int, int]]]
    ) -> list[list[str]]:
        """
        Extract contexts for all references.

        Args:
            texts: List of document text strings
            references: List of lists of tuples containing (start, end) positions of references

        Returns:
            List of lists of context strings, matching the structure of references
        """
        contexts = []
        for text, doc_references in zip(texts, references, strict=True):
            doc_contexts = []
            for start, end in doc_references:
                context = self._extract_context(text, start, end)
                doc_contexts.append(context)
            contexts.append(doc_contexts)
        return contexts

    def _embed_contexts(self, contexts: list[list[str]]) -> None:
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

            # Store embeddings in cache with context as key. The encoder
            # returns one embedding per input, so strict= only matters if a
            # stand-in model breaks that contract; truncating is the
            # long-standing behaviour and is kept deliberately.
            for context, embedding in zip(unique_contexts, embeddings, strict=False):
                self.context_embeddings[context] = embedding

    def _gather_candidates(
        self,
        texts: list[str],
        references: list[list[tuple[int, int]]],
        candidates: list[list[list["Feature"]]],
        results: list[list[tuple[str, str] | None]],
        method: str,
        tiers: int,
    ) -> None:
        """
        Gather candidates for unresolved references using the specified search method.

        Args:
            texts: List of document text strings
            references: List of lists of tuples containing (start, end) positions of references
            candidates: Nested list of candidate lists for each reference (modified in-place)
            results: Nested list of current results to determine which references need candidates
            method: Search method to use
            tiers: Number of rank tiers to include
        """
        for _doc_idx, (text, doc_references, doc_candidates, doc_results) in enumerate(
            zip(texts, references, candidates, results, strict=True)
        ):
            for ref_idx, ((start, end), result) in enumerate(
                zip(doc_references, doc_results, strict=True)
            ):
                # Skip already resolved references
                if result is not None:
                    continue

                # Search for new candidates and merge with existing ones, avoiding duplicates
                reference_text = text[start:end]
                new_candidates = self.gazetteer.search(
                    reference_text, method, tiers=tiers
                )
                existing_ids = {c.id for c in doc_candidates[ref_idx]}
                for candidate in new_candidates:
                    if candidate.id not in existing_ids:
                        doc_candidates[ref_idx].append(candidate)

    def _embed_candidates(
        self,
        candidates: list[list[list["Feature"]]],
        results: list[list[tuple[str, str] | None]],
    ) -> None:
        """
        Generate embeddings for candidates that need to be processed.

        Args:
            candidates: Nested list of candidate lists for each reference
            results: Nested list of current results to determine which candidates need embedding
        """
        # Collect unique candidates that need embedding
        candidates_to_embed = {}  # Use dict to avoid duplicates: id -> candidate

        for doc_candidates, doc_results in zip(candidates, results, strict=True):
            for candidate_list, result in zip(doc_candidates, doc_results, strict=True):
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

            # Store embeddings in cache. As above, the encoder's output
            # length is its own contract rather than one enforced here.
            for candidate, embedding in zip(candidates_list, embeddings, strict=False):
                self.candidate_embeddings[candidate.id] = embedding

    def _evaluate_candidates(
        self,
        contexts: list[list[str]],
        candidates: list[list[list["Feature"]]],
        results: list[list[tuple[str, str] | None]],
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
        for _doc_idx, (doc_contexts, doc_candidates, doc_results) in enumerate(
            zip(contexts, candidates, results, strict=True)
        ):
            for ref_idx, (context, candidate_list, result) in enumerate(
                zip(doc_contexts, doc_candidates, doc_results, strict=True)
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
                        best_candidate.identifier,
                    )

    def _extract_context(self, text: str, start: int, end: int) -> str:
        """
        Extract context around a single reference, respecting model token limits.

        The whole document is used when it fits. Otherwise the sentence holding
        the reference is grown outwards, a sentence at a time, for as long as
        the encoder's token budget allows.

        Args:
            text: Full document text
            start: Start position of the reference
            end: End position of the reference

        Returns:
            Context string for the reference
        """
        token_limit = self._token_limit()

        if self._document_tokens(text) <= token_limit:
            return text

        sentences = self._sentences(text)
        target_idx = self._locate_sentence(sentences, start, end)
        window = self._expand_window(sentences, target_idx, token_limit)
        return " ".join(sent.text for sent in window)

    def _token_limit(self) -> int:
        """
        The number of tokens available for a context.

        Returns:
            The model's maximum sequence length, less the special tokens
            ([CLS] and [SEP] for BERT-like models)

        Raises:
            ValueError: If the model advertises no maximum sequence length
        """
        max_seq_length = self.transformer.get_max_seq_length()
        if max_seq_length is None:
            raise ValueError(
                f"Model '{self.model_name}' does not report a maximum sequence "
                "length, so reference context cannot be sized"
            )
        return max_seq_length - 2

    def _document_tokens(self, text: str) -> int:
        """
        The token count of a whole document, computed once per document.

        Args:
            text: Full document text

        Returns:
            Number of tokens in the document
        """
        if text not in self.doc_tokens:
            self.doc_tokens[text] = len(self.tokenizer.tokenize(text))
        return self.doc_tokens[text]

    def _sentences(self, text: str) -> list["spacy.tokens.Span"]:
        """
        The document's sentences, parsed once per document.

        Args:
            text: Full document text

        Returns:
            The document's sentence spans, in order
        """
        if text not in self.doc_objects:
            self.doc_objects[text] = self.nlp(text)
        return list(self.doc_objects[text].sents)

    @staticmethod
    def _locate_sentence(
        sentences: list["spacy.tokens.Span"], start: int, end: int
    ) -> int:
        """
        Find the index of the sentence containing a reference.

        Args:
            sentences: The document's sentence spans
            start: Start position of the reference
            end: End position of the reference

        Returns:
            Index into ``sentences``

        Raises:
            ValueError: If the reference falls in no sentence -- a span past the
                end of the text, or in a gap the splitter left uncovered. This
                previously surfaced as "None is not in list".
        """
        for index, sent in enumerate(sentences):
            if sent.start_char <= start < sent.end_char:
                return index
        raise ValueError(f"No sentence contains reference at position {start}-{end}")

    def _expand_window(
        self,
        sentences: list["spacy.tokens.Span"],
        target_idx: int,
        token_limit: int,
    ) -> list["spacy.tokens.Span"]:
        """
        Grow a sentence window outwards while it stays within the token budget.

        Expansion alternates between the preceding and following sentence and
        stops as soon as neither fits, so the reference stays roughly centred.

        Args:
            sentences: The document's sentence spans
            target_idx: Index of the sentence holding the reference
            token_limit: Tokens available for the whole context

        Returns:
            The contiguous run of sentences to use as context
        """
        window = [sentences[target_idx]]
        tokens_count = len(self.tokenizer.tokenize(sentences[target_idx].text))
        first, last = target_idx, target_idx

        while True:
            expanded = False

            if first > 0:
                candidate = sentences[first - 1]
                cost = len(self.tokenizer.tokenize(candidate.text))
                if tokens_count + cost <= token_limit:
                    window.insert(0, candidate)
                    tokens_count += cost
                    first -= 1
                    expanded = True

            if last < len(sentences) - 1:
                candidate = sentences[last + 1]
                cost = len(self.tokenizer.tokenize(candidate.text))
                if tokens_count + cost <= token_limit:
                    window.append(candidate)
                    tokens_count += cost
                    last += 1
                    expanded = True

            if not expanded:
                return window

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

        # Use the attribute map that was set during initialization
        attr_map = self.attribute_map

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
        candidate_embeddings: list[torch.Tensor],
    ) -> list[float]:
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
        texts: list[str],
        references: list[list[tuple[int, int]]],
        referents: list[list[tuple[str, str]]],
        output_path: str | Path,
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
        texts: list[str],
        references: list[list[tuple[int, int]]],
        referents: list[list[tuple[str, str]]],
    ) -> dict[str, list]:
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

        for text, doc_references, doc_referents in zip(
            texts, references, referents, strict=True
        ):
            for (start, end), (_gazetteer_name, identifier) in zip(
                doc_references, doc_referents, strict=True
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
                    label = 1 if candidate.identifier == identifier else 0

                    # Add as training example
                    sentence1_texts.append(context)
                    sentence2_texts.append(description)
                    labels.append(label)

        return {
            "sentence1": sentence1_texts,
            "sentence2": sentence2_texts,
            "label": labels,
        }
