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


# Throughput and display only: neither changes the embeddings that come back.
_ENCODE_BATCH_SIZE = 32  # pragma: no mutate
_SHOW_ENCODE_PROGRESS = True  # pragma: no mutate


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
        **extra_config,
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
            **extra_config: Additional configuration a subclass wants recorded
                          in the module id, so two resolvers that differ only
                          in a subclass parameter do not share one.
        """
        # Initialize parent with the parameters
        super().__init__(
            model_name=model_name,
            gazetteer_name=gazetteer_name,
            min_similarity=min_similarity,
            max_tiers=max_tiers,
            attribute_map=attribute_map,
            **extra_config,
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
        self.transformer = self._load_transformer(model_name)
        self.tokenizer = self._load_tokenizer(model_name)

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

    def _load_transformer(self, model_name: str, **kwargs) -> SentenceTransformer:
        """
        Load the embedding model.

        A hook rather than a direct call so a subclass whose checkpoint ships
        its own modelling code can pass the flags that need.

        Args:
            model_name: HuggingFace checkpoint to load
            **kwargs: Extra arguments for the SentenceTransformer constructor

        Returns:
            The loaded model
        """
        return SentenceTransformer(model_name, **kwargs)

    def _load_tokenizer(self, model_name: str, **kwargs) -> PreTrainedTokenizerBase:
        """
        Load the tokenizer used to size reference contexts.

        Args:
            model_name: HuggingFace checkpoint to load the tokenizer of
            **kwargs: Extra arguments for ``AutoTokenizer.from_pretrained``

        Returns:
            The loaded tokenizer
        """
        return AutoTokenizer.from_pretrained(model_name, **kwargs)

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
            # pragma: no mutate start - progress prose, not behaviour; the
            # download and the reload below are what the tests pin.
            print(f"Downloading spaCy model '{model_name}'...")
            # pragma: no mutate end
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
        results = self._empty_results(references)
        candidates = self._empty_candidates(references)

        # Iterative search strategy with increasing tiers
        for tiers in range(1, self.max_tiers + 1):
            self._search_tier(texts, references, contexts, candidates, results, tiers)

            # If all references resolved, we can stop
            if self._all_resolved(results):
                break

        return results

    @staticmethod
    def _empty_results(
        references: list[list[tuple[int, int]]],
    ) -> list[list[tuple[str, str] | None]]:
        """
        One empty result slot per reference, to be filled as they resolve.

        Args:
            references: Per-document reference spans

        Returns:
            A None per reference, nested by document
        """
        return [[None for _ in doc_refs] for doc_refs in references]

    @staticmethod
    def _empty_candidates(
        references: list[list[tuple[int, int]]],
    ) -> list[list[list["Feature"]]]:
        """
        One empty candidate list per reference.

        Args:
            references: Per-document reference spans

        Returns:
            An empty list per reference, nested by document
        """
        return [[[] for _ in doc_refs] for doc_refs in references]

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
                # pragma: no mutate start - last statement of the loop with
                # nothing after it, so `return` behaves identically.
                break
                # pragma: no mutate end

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

    def _encode(self, texts: list[str], role: str) -> "torch.Tensor":
        """
        Embed a batch of strings with the sentence transformer.

        Args:
            texts: Strings to embed
            role: What the strings are -- ``"context"`` for reference contexts
                  or ``"candidate"`` for candidate descriptions. Symmetric
                  models ignore it; models with separate query and document
                  prompts override this method and use it. Required, so that
                  a new call site has to say which side it is embedding.

        Returns:
            One embedding per input string, in the same order
        """
        # pragma: no mutate start - batch size and the progress bar are
        # throughput and display, not behaviour; convert_to_tensor and the
        # texts themselves are pinned by tests on the subclass that overrides
        # this method, which is where an encode call is worth checking.
        return self.transformer.encode(
            texts,
            convert_to_tensor=True,
            batch_size=_ENCODE_BATCH_SIZE,
            show_progress_bar=_SHOW_ENCODE_PROGRESS,
        )
        # pragma: no mutate end

    def _contexts_needing_embedding(self, contexts: list[list[str]]) -> list[str]:
        """
        The distinct contexts that are not already in the cache.

        Args:
            contexts: List of lists of context strings

        Returns:
            Sorted unique contexts still to encode
        """
        return sorted(
            {
                context
                for doc_contexts in contexts
                for context in doc_contexts
                if context not in self.context_embeddings
            }
        )

    def _embed_contexts(self, contexts: list[list[str]]) -> None:
        """
        Generate embeddings for contexts, avoiding duplicate work.

        Args:
            contexts: List of lists of context strings
        """
        to_encode = self._contexts_needing_embedding(contexts)
        if not to_encode:
            return

        # The encoder returns one embedding per input, so strict= only matters
        # if a stand-in model breaks that contract; truncating is the
        # long-standing behaviour and is kept deliberately.
        embeddings = self._encode(to_encode, role="context")
        # One embedding per input by construction, so strict= is immaterial.
        pairs = zip(to_encode, embeddings, strict=False)  # pragma: no mutate
        for context, embedding in pairs:
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
        for text, doc_references, doc_candidates, doc_results in zip(
            texts, references, candidates, results, strict=True
        ):
            for ref_idx, ((start, end), result) in enumerate(
                zip(doc_references, doc_results, strict=True)
            ):
                # Skip already resolved references
                if result is not None:
                    continue

                found = self.gazetteer.search(text[start:end], method, tiers=tiers)
                self._merge_candidates(doc_candidates[ref_idx], found)

    @staticmethod
    def _merge_candidates(existing: list["Feature"], found: list["Feature"]) -> None:
        """
        Append newly found candidates, skipping ones already present.

        Args:
            existing: This reference's candidates so far, extended in place
            found: Candidates the gazetteer just returned
        """
        existing_ids = {candidate.id for candidate in existing}
        existing.extend(
            candidate for candidate in found if candidate.id not in existing_ids
        )

    @staticmethod
    def _unresolved_candidate_lists(
        candidates: list[list[list["Feature"]]],
        results: list[list[tuple[str, str] | None]],
    ) -> list[list["Feature"]]:
        """
        The candidate lists belonging to references that are still unresolved.

        Args:
            candidates: Nested list of candidate lists for each reference
            results: Nested list of current results

        Returns:
            One candidate list per unresolved reference
        """
        return [
            candidate_list
            for doc_candidates, doc_results in zip(candidates, results, strict=True)
            for candidate_list, result in zip(doc_candidates, doc_results, strict=True)
            if result is None
        ]

    def _candidates_needing_embedding(
        self,
        candidates: list[list[list["Feature"]]],
        results: list[list[tuple[str, str] | None]],
    ) -> list["Feature"]:
        """
        The distinct candidates of unresolved references that are not cached.

        Args:
            candidates: Nested list of candidate lists for each reference
            results: Nested list of current results

        Returns:
            Unique candidates still to encode, in first-seen order
        """
        pending: dict[int, Feature] = {}
        for candidate_list in self._unresolved_candidate_lists(candidates, results):
            for candidate in candidate_list:
                if candidate.id not in self.candidate_embeddings:
                    pending[candidate.id] = candidate
        return list(pending.values())

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
        pending = self._candidates_needing_embedding(candidates, results)
        if not pending:
            return

        descriptions = [self._generate_description(candidate) for candidate in pending]
        # As with contexts, the encoder's output length is its own contract.
        embeddings = self._encode(descriptions, role="candidate")
        # As above: one embedding per description, so strict= is immaterial.
        pairs = zip(pending, embeddings, strict=False)  # pragma: no mutate
        for candidate, embedding in pairs:
            self.candidate_embeddings[candidate.id] = embedding

    def _evaluate_candidates(
        self,
        contexts: list[list[str]],
        candidates: list[list[list["Feature"]]],
        results: list[list[tuple[str, str] | None]],
        min_similarity: float,
    ) -> None:
        """
        Evaluate candidates against reference contexts and update results.

        Args:
            contexts: List of lists of context strings
            candidates: Nested list of candidate lists for each reference
            results: Nested list of current results (modified in-place)
            min_similarity: Similarity a candidate must reach to be accepted
        """
        for doc_contexts, doc_candidates, doc_results in zip(
            contexts, candidates, results, strict=True
        ):
            self._evaluate_document(
                doc_contexts, doc_candidates, doc_results, min_similarity
            )

    def _evaluate_document(
        self,
        doc_contexts: list[str],
        doc_candidates: list[list["Feature"]],
        doc_results: list[tuple[str, str] | None],
        min_similarity: float,
    ) -> None:
        """
        Resolve one document's still-unresolved references, in place.

        Args:
            doc_contexts: Context string per reference
            doc_candidates: Candidate list per reference
            doc_results: Result slot per reference, filled in place
            min_similarity: Similarity a candidate must reach to be accepted
        """
        for ref_idx, (context, candidate_list, result) in enumerate(
            zip(doc_contexts, doc_candidates, doc_results, strict=True)
        ):
            # Skip references that are already resolved or have nothing to rank
            if result is not None or not candidate_list:
                continue

            referent = self._best_referent(context, candidate_list, min_similarity)
            if referent is not None:
                doc_results[ref_idx] = referent

    def _best_referent(
        self,
        context: str,
        candidate_list: list["Feature"],
        min_similarity: float,
    ) -> tuple[str, str] | None:
        """
        Pick the candidate most similar to a reference's context.

        Args:
            context: The reference's context string
            candidate_list: Candidates to rank, all already embedded
            min_similarity: Similarity a candidate must reach to be accepted

        Returns:
            A (gazetteer_name, identifier) pair, or None when the best
            candidate is not similar enough
        """
        similarities = self._calculate_similarities(
            self.context_embeddings[context],
            [self.candidate_embeddings[candidate.id] for candidate in candidate_list],
        )
        best_idx = max(range(len(similarities)), key=lambda j: similarities[j])
        if similarities[best_idx] < min_similarity:
            return None
        return self.gazetteer_name, candidate_list[best_idx].identifier

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
            # pragma: no mutate start - wording only; a test pins the type and
            # that the message names the model.
            raise ValueError(
                f"Model '{self.model_name}' does not report a maximum sequence "
                "length, so reference context cannot be sized"
            )
            # pragma: no mutate end
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

    def _sentence_tokens(self, sentence: "spacy.tokens.Span") -> int:
        """
        The token cost of one sentence.

        Args:
            sentence: The sentence to measure

        Returns:
            Number of tokens the encoder would spend on it
        """
        return len(self.tokenizer.tokenize(sentence.text))

    def _affordable_cost(
        self,
        sentences: list["spacy.tokens.Span"],
        index: int,
        remaining: int,
    ) -> int | None:
        """
        The cost of a neighbouring sentence, if it exists and still fits.

        Args:
            sentences: The document's sentence spans
            index: Index of the neighbour being considered
            remaining: Tokens left in the budget

        Returns:
            The neighbour's token cost, or None when there is no such sentence
            or it would not fit
        """
        if index < 0 or index >= len(sentences):
            return None
        cost = self._sentence_tokens(sentences[index])
        return cost if cost <= remaining else None

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
        remaining = token_limit - self._sentence_tokens(sentences[target_idx])
        first, last = target_idx, target_idx

        while True:
            # pragma: no mutate - only ever read as `if not grew`, so False and
            # None are indistinguishable; the mutant is equivalent.
            grew = False  # pragma: no mutate

            cost = self._affordable_cost(sentences, first - 1, remaining)
            if cost is not None:
                first -= 1
                remaining -= cost
                window.insert(0, sentences[first])
                grew = True

            cost = self._affordable_cost(sentences, last + 1, remaining)
            if cost is not None:
                last += 1
                remaining -= cost
                window.append(sentences[last])
                grew = True

            if not grew:
                return window

    def _admin_levels(self, location_data: dict) -> list[str]:
        """
        Administrative place names for a candidate, most specific first.

        Args:
            location_data: The candidate's gazetteer attributes

        Returns:
            The non-empty administrative names, in level3..level1 order
        """
        values = []
        for level in ("level3", "level2", "level1"):
            if level in self.attribute_map:
                value = location_data.get(self.attribute_map[level])
                if value:
                    values.append(value)
        return values

    def _generate_description(self, candidate: "Feature") -> str:
        """
        Generate a textual description for a single candidate location.

        Args:
            candidate: Feature object

        Returns:
            Location description string
        """
        location_data = candidate.data
        attr_map = self.attribute_map
        description_parts = []

        feature_name = location_data.get(attr_map["name"])
        if feature_name:
            description_parts.append(feature_name)

        feature_type = location_data.get(attr_map["type"])
        if feature_type:
            description_parts.append(f"({feature_type})")

        admin_levels = self._admin_levels(location_data)
        if admin_levels:
            description_parts.append("in")
            description_parts.append(", ".join(admin_levels))

        return " ".join(description_parts).strip()

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
        # pragma: no mutate start - dim=1 is also torch's default, so a
        # mutant that drops it computes exactly the same similarities.
        similarities = torch.nn.functional.cosine_similarity(
            context_embedding.unsqueeze(0), candidate_tensor, dim=1
        )
        # pragma: no mutate end

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
