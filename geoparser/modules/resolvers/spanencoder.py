import json
import random
import typing as t
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import torch
import torch.nn.functional as F
from torch import nn
from transformers import AutoConfig, AutoModel, AutoTokenizer, logging

from geoparser.gazetteer.gazetteer import Gazetteer
from geoparser.modules.resolvers import Resolver

if t.TYPE_CHECKING:
    from geoparser.db.models.feature import Feature

logging.set_verbosity_error()

HEAD_FILE = "span_projection_head.pt"
CONFIG_FILE = "span_encoder_config.json"


class SpanEncoderResolver(Resolver):
    """
    A resolver that disambiguates the exact place mention using span pooling.

    Both sides of the comparison are encoded by a single shared transformer:

    - Mentions are embedded by encoding their document context and pooling the
      hidden states of the mention's own tokens (start state, end state, and
      span mean), so each mention in a document gets its own embedding.
    - Gazetteer candidates are embedded by serializing their textual attributes
      into a structured string (``name | type | admin3 > admin2 > admin1``) and
      pooling the name's tokens the same way, with the remaining attributes
      acting as context.

    Resolution scores candidates by cosine similarity between the two
    embeddings, mirroring the tiered candidate search of the original
    SentenceTransformerResolver, and always assigns the best-scoring candidate
    encountered if no candidate passes the similarity threshold.
    """

    NAME = "SpanEncoderResolver"

    # Gazetteer-specific attribute mappings for entity serialization
    GAZETTEER_ATTRIBUTE_MAP = {
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
        model_name: str = "answerdotai/ModernBERT-base",
        gazetteer_name: str = "geonames",
        min_similarity: float = 0.6,
        max_tiers: int = 3,
        attribute_map: dict = None,
        embedding_dim: int = 256,
        max_context_tokens: int = 512,
        max_document_tokens: int = 8192,
    ):
        """
        Initialize the SpanEncoderResolver.

        Args:
            model_name: HuggingFace model name or path to a fine-tuned
                SpanEncoderResolver directory
            gazetteer_name: Name of the gazetteer to search
            min_similarity: Similarity threshold used to stop candidate search
                expansion (the best candidate overall is assigned regardless)
            max_tiers: Maximum number of tiers to expand through search methods
            attribute_map: Optional custom attribute mapping for the gazetteer
            embedding_dim: Dimensionality of the shared embedding space
            max_context_tokens: Token window around a mention used during
                training and for documents longer than max_document_tokens
            max_document_tokens: Maximum document length for single-pass encoding
        """
        super().__init__(
            model_name=model_name,
            gazetteer_name=gazetteer_name,
            min_similarity=min_similarity,
            max_tiers=max_tiers,
            attribute_map=attribute_map,
            embedding_dim=embedding_dim,
            max_context_tokens=max_context_tokens,
            max_document_tokens=max_document_tokens,
        )

        self.model_name = model_name
        self.gazetteer_name = gazetteer_name
        self.min_similarity = min_similarity
        self.max_tiers = max_tiers
        self.embedding_dim = embedding_dim
        self.max_context_tokens = max_context_tokens
        self.max_document_tokens = max_document_tokens

        self.attribute_map = self._validate_and_set_attribute_map(
            gazetteer_name, attribute_map
        )

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # Load backbone (and projection head if loading a fine-tuned directory)
        saved_config = self._load_saved_config(model_name)
        if saved_config is not None:
            self.embedding_dim = saved_config["embedding_dim"]
        model_kwargs = {}
        if hasattr(AutoConfig.from_pretrained(model_name), "reference_compile"):
            # Avoid torch.compile at load time (requires a working Triton
            # toolchain); plain eager/SDPA execution works everywhere.
            model_kwargs["reference_compile"] = False
        self.encoder = AutoModel.from_pretrained(model_name, **model_kwargs)
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        hidden_size = self.encoder.config.hidden_size
        self.projection_head = nn.Linear(3 * hidden_size, self.embedding_dim)
        if saved_config is not None:
            head_state = torch.load(
                Path(model_name) / HEAD_FILE, map_location="cpu", weights_only=True
            )
            self.projection_head.load_state_dict(head_state)

        self.encoder.to(self.device)
        self.projection_head.to(self.device)
        self.encoder.eval()

        self.gazetteer = Gazetteer(gazetteer_name)

        # In-memory cache of candidate embeddings for this session
        self.candidate_embeddings: Dict[int, torch.Tensor] = {}

    # ------------------------------------------------------------------
    # Setup helpers
    # ------------------------------------------------------------------

    def _validate_and_set_attribute_map(
        self, gazetteer_name: str, attribute_map: dict = None
    ) -> dict:
        if attribute_map is None:
            if gazetteer_name not in self.GAZETTEER_ATTRIBUTE_MAP:
                raise ValueError(
                    f"Gazetteer '{gazetteer_name}' is not configured in "
                    f"GAZETTEER_ATTRIBUTE_MAP. Please provide a custom "
                    f"attribute_map parameter."
                )
            return self.GAZETTEER_ATTRIBUTE_MAP[gazetteer_name]
        return attribute_map

    @staticmethod
    def _load_saved_config(model_name: str) -> Optional[dict]:
        config_path = Path(model_name) / CONFIG_FILE
        if config_path.is_file():
            with open(config_path) as f:
                return json.load(f)
        return None

    def save(self, output_path: Union[str, Path]) -> None:
        """Save backbone, projection head, and encoder config to a directory."""
        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)
        self.encoder.save_pretrained(output_path)
        self.tokenizer.save_pretrained(output_path)
        torch.save(self.projection_head.state_dict(), output_path / HEAD_FILE)
        with open(output_path / CONFIG_FILE, "w") as f:
            json.dump({"embedding_dim": self.embedding_dim}, f)

    # ------------------------------------------------------------------
    # Encoding
    # ------------------------------------------------------------------

    def _pool_spans(
        self,
        hidden_states: torch.Tensor,
        attention_mask: torch.Tensor,
        token_spans: List[List[Tuple[int, int]]],
    ) -> torch.Tensor:
        """
        Pool hidden states over token spans and project to the embedding space.

        Args:
            hidden_states: (batch, seq, hidden) encoder output
            attention_mask: (batch, seq) attention mask
            token_spans: For each batch item, a list of (first_token, last_token)
                inclusive index pairs to pool

        Returns:
            (n_spans_total, embedding_dim) L2-normalized embeddings, ordered by
            batch item then span
        """
        pooled = []
        for batch_idx, spans in enumerate(token_spans):
            for first, last in spans:
                span_states = hidden_states[batch_idx, first : last + 1]
                vector = torch.cat(
                    [
                        hidden_states[batch_idx, first],
                        hidden_states[batch_idx, last],
                        span_states.mean(dim=0),
                    ]
                )
                pooled.append(vector)
        pooled = torch.stack(pooled)
        return F.normalize(self.projection_head(pooled), dim=-1)

    @staticmethod
    def _char_span_to_token_span(
        offsets: List[Tuple[int, int]], start: int, end: int
    ) -> Optional[Tuple[int, int]]:
        """
        Find the inclusive token index range overlapping a character span.

        Special tokens (offset (0, 0)) are skipped.
        """
        first, last = None, None
        for idx, (token_start, token_end) in enumerate(offsets):
            if token_end <= token_start:
                continue
            if token_start < end and token_end > start:
                if first is None:
                    first = idx
                last = idx
        if first is None:
            return None
        return (first, last)

    def _encode_mentions(
        self,
        texts: List[str],
        references: List[List[Tuple[int, int]]],
        batch_token_budget: int = 16384,
        show_progress: bool = False,
    ) -> List[List[Optional[torch.Tensor]]]:
        """
        Encode all mentions with one encoder pass per document.

        Documents longer than max_document_tokens fall back to per-mention
        token windows of max_context_tokens.

        Returns:
            Nested list of mention embeddings matching the references structure
        """
        results: List[List[Optional[torch.Tensor]]] = [
            [None for _ in doc_refs] for doc_refs in references
        ]

        # Tokenize all documents once to determine lengths and offsets
        encodings = self.tokenizer(
            texts,
            add_special_tokens=True,
            return_offsets_mapping=True,
            truncation=False,
        )

        # Partition into single-pass documents and long-document fallbacks
        single_pass: List[int] = []
        fallback: List[int] = []
        for doc_idx, input_ids in enumerate(encodings["input_ids"]):
            if not references[doc_idx]:
                continue
            if len(input_ids) <= self.max_document_tokens:
                single_pass.append(doc_idx)
            else:
                fallback.append(doc_idx)

        # Batch single-pass documents by a token budget
        batches: List[List[int]] = []
        current: List[int] = []
        current_max_len = 0
        for doc_idx in sorted(
            single_pass, key=lambda i: len(encodings["input_ids"][i])
        ):
            doc_len = len(encodings["input_ids"][doc_idx])
            new_max = max(current_max_len, doc_len)
            if current and new_max * (len(current) + 1) > batch_token_budget:
                batches.append(current)
                current, current_max_len = [], 0
                new_max = doc_len
            current.append(doc_idx)
            current_max_len = new_max
        if current:
            batches.append(current)

        iterator = batches
        if show_progress:
            from tqdm import tqdm

            iterator = tqdm(batches, desc="Encoding documents")

        for batch in iterator:
            batch_encodings = self.tokenizer(
                [texts[i] for i in batch],
                add_special_tokens=True,
                return_offsets_mapping=True,
                padding=True,
                truncation=True,
                max_length=self.max_document_tokens,
                return_tensors="pt",
            )
            offsets = batch_encodings.pop("offset_mapping")
            batch_encodings = {
                k: v.to(self.device) for k, v in batch_encodings.items()
            }

            token_spans: List[List[Tuple[int, int]]] = []
            span_positions: List[Tuple[int, int]] = []  # (doc_idx, ref_idx)
            for batch_pos, doc_idx in enumerate(batch):
                doc_offsets = offsets[batch_pos].tolist()
                doc_spans = []
                for ref_idx, (start, end) in enumerate(references[doc_idx]):
                    token_span = self._char_span_to_token_span(
                        doc_offsets, start, end
                    )
                    if token_span is not None:
                        doc_spans.append(token_span)
                        span_positions.append((doc_idx, ref_idx))
                token_spans.append(doc_spans)

            if not span_positions:
                continue

            with torch.inference_mode():
                hidden_states = self.encoder(**batch_encodings).last_hidden_state
                embeddings = self._pool_spans(
                    hidden_states, batch_encodings["attention_mask"], token_spans
                )

            for (doc_idx, ref_idx), embedding in zip(span_positions, embeddings):
                results[doc_idx][ref_idx] = embedding

        # Fallback: long documents, per-mention token windows
        for doc_idx in fallback:
            for ref_idx, (start, end) in enumerate(references[doc_idx]):
                window_ids, first, last = self._mention_token_window(
                    encodings["input_ids"][doc_idx],
                    encodings["offset_mapping"][doc_idx],
                    start,
                    end,
                    self.max_context_tokens,
                )
                if window_ids is None:
                    continue
                input_ids = torch.tensor([window_ids], device=self.device)
                attention_mask = torch.ones_like(input_ids)
                with torch.inference_mode():
                    hidden_states = self.encoder(
                        input_ids=input_ids, attention_mask=attention_mask
                    ).last_hidden_state
                    embedding = self._pool_spans(
                        hidden_states, attention_mask, [[(first, last)]]
                    )[0]
                results[doc_idx][ref_idx] = embedding

        return results

    def _mention_token_window(
        self,
        input_ids: List[int],
        offsets: List[Tuple[int, int]],
        start: int,
        end: int,
        window_tokens: int,
    ) -> Tuple[Optional[List[int]], Optional[int], Optional[int]]:
        """
        Extract a token window centered on a mention from a full-document encoding.

        Returns:
            (window input_ids, first span token index within the window,
            last span token index within the window), or (None, None, None)
            if the mention cannot be located
        """
        token_span = self._char_span_to_token_span(list(offsets), start, end)
        if token_span is None:
            return None, None, None
        first, last = token_span

        span_length = last - first + 1
        remaining = max(window_tokens - span_length, 0)
        window_start = max(first - remaining // 2, 0)
        window_end = min(window_start + window_tokens, len(input_ids))
        window_start = max(window_end - window_tokens, 0)

        window_ids = list(input_ids[window_start:window_end])
        return window_ids, first - window_start, last - window_start

    def _serialize_candidate(self, candidate: "Feature") -> Tuple[str, str]:
        """
        Serialize a candidate's textual attributes into a structured string.

        Returns:
            (serialized string, name substring) — the name substring is the
            leading field, whose token span is pooled
        """
        location_data = candidate.data or {}
        attr_map = self.attribute_map

        name = location_data.get(attr_map["name"]) or ""
        feature_type = location_data.get(attr_map["type"])

        parts = [name]
        if feature_type:
            parts.append(str(feature_type))

        admin_levels = []
        for level in ["level3", "level2", "level1"]:
            if level in attr_map:
                value = location_data.get(attr_map[level])
                if value:
                    admin_levels.append(str(value))
        if admin_levels:
            parts.append(" > ".join(admin_levels))

        return " | ".join(parts), name

    def _encode_candidate_strings(
        self,
        serializations: List[Tuple[str, str]],
        batch_size: int = 128,
        show_progress: bool = False,
    ) -> torch.Tensor:
        """
        Encode serialized candidate strings with name-span pooling.

        Args:
            serializations: List of (serialized string, name substring) pairs

        Returns:
            (n, embedding_dim) L2-normalized embeddings
        """
        embeddings = []
        indices = range(0, len(serializations), batch_size)
        if show_progress:
            from tqdm import tqdm

            indices = tqdm(indices, desc="Encoding candidates")

        for batch_start in indices:
            batch = serializations[batch_start : batch_start + batch_size]
            texts = [s for s, _ in batch]
            encodings = self.tokenizer(
                texts,
                add_special_tokens=True,
                return_offsets_mapping=True,
                padding=True,
                truncation=True,
                max_length=self.max_context_tokens,
                return_tensors="pt",
            )
            offsets = encodings.pop("offset_mapping")
            encodings = {k: v.to(self.device) for k, v in encodings.items()}

            token_spans: List[List[Tuple[int, int]]] = []
            for item_idx, (text, name) in enumerate(batch):
                span = None
                if name:
                    span = self._char_span_to_token_span(
                        offsets[item_idx].tolist(), 0, len(name)
                    )
                if span is None:
                    # Fall back to pooling over all non-special tokens
                    non_special = [
                        i
                        for i, (s, e) in enumerate(offsets[item_idx].tolist())
                        if e > s
                    ]
                    span = (non_special[0], non_special[-1]) if non_special else (0, 0)
                token_spans.append([span])

            with torch.inference_mode():
                hidden_states = self.encoder(**encodings).last_hidden_state
                batch_embeddings = self._pool_spans(
                    hidden_states, encodings["attention_mask"], token_spans
                )
            embeddings.append(batch_embeddings)

        return torch.cat(embeddings, dim=0)

    def _embed_new_candidates(self, candidates: List["Feature"]) -> None:
        """Encode and cache embeddings for candidates not yet in the cache."""
        new_candidates = [
            c for c in candidates if c.id not in self.candidate_embeddings
        ]
        # Deduplicate by feature id
        unique = {c.id: c for c in new_candidates}
        if not unique:
            return
        candidate_list = list(unique.values())
        serializations = [self._serialize_candidate(c) for c in candidate_list]
        embeddings = self._encode_candidate_strings(serializations)
        for candidate, embedding in zip(candidate_list, embeddings):
            self.candidate_embeddings[candidate.id] = embedding

    # ------------------------------------------------------------------
    # Prediction
    # ------------------------------------------------------------------

    def predict(
        self, texts: t.List[str], references: t.List[t.List[t.Tuple[int, int]]]
    ) -> t.List[t.List[t.Union[t.Tuple[str, str], None]]]:
        """
        Predict referents for multiple references using iterative candidate search.

        Uses the same tiered search ladder as the SentenceTransformerResolver
        (exact, phrase, partial, fuzzy with increasing tiers). A reference is
        finalized early when a candidate reaches min_similarity; once the
        ladder is exhausted, the best-scoring candidate seen so far is assigned.

        Returns:
            Nested list of (gazetteer_name, identifier) tuples or None
        """
        if not texts:
            return []

        mention_embeddings = self._encode_mentions(texts, references)

        results: List[List[Optional[Tuple[str, str]]]] = [
            [None for _ in doc_refs] for doc_refs in references
        ]
        # Best candidate seen so far per reference: (score, identifier)
        best_seen: List[List[Optional[Tuple[float, str]]]] = [
            [None for _ in doc_refs] for doc_refs in references
        ]
        seen_candidate_ids: List[List[set]] = [
            [set() for _ in doc_refs] for doc_refs in references
        ]

        search_methods = ["exact", "phrase", "partial", "fuzzy"]

        for tiers in range(1, self.max_tiers + 1):
            for method in search_methods:
                if method == "exact" and tiers > 1:
                    continue

                for doc_idx, (text, doc_refs) in enumerate(zip(texts, references)):
                    for ref_idx, (start, end) in enumerate(doc_refs):
                        if results[doc_idx][ref_idx] is not None:
                            continue
                        mention_embedding = mention_embeddings[doc_idx][ref_idx]
                        if mention_embedding is None:
                            continue

                        surface = text[start:end]
                        candidates = self.gazetteer.search(
                            surface, method, tiers=tiers
                        )
                        new_candidates = [
                            c
                            for c in candidates
                            if c.id not in seen_candidate_ids[doc_idx][ref_idx]
                        ]
                        if not new_candidates:
                            continue
                        seen_candidate_ids[doc_idx][ref_idx].update(
                            c.id for c in new_candidates
                        )

                        self._embed_new_candidates(new_candidates)
                        candidate_matrix = torch.stack(
                            [
                                self.candidate_embeddings[c.id]
                                for c in new_candidates
                            ]
                        )
                        scores = candidate_matrix @ mention_embedding
                        top_score, top_idx = scores.max(dim=0)
                        top_score = top_score.item()
                        top_candidate = new_candidates[top_idx.item()]

                        current_best = best_seen[doc_idx][ref_idx]
                        if current_best is None or top_score > current_best[0]:
                            best_seen[doc_idx][ref_idx] = (
                                top_score,
                                top_candidate.location_id_value,
                            )

                        if top_score >= self.min_similarity:
                            results[doc_idx][ref_idx] = (
                                self.gazetteer_name,
                                top_candidate.location_id_value,
                            )

                if all(
                    all(r is not None for r in doc_results)
                    for doc_results in results
                ):
                    break
            if all(
                all(r is not None for r in doc_results) for doc_results in results
            ):
                break

        # Final assignment: best candidate seen so far, regardless of threshold
        for doc_idx, doc_results in enumerate(results):
            for ref_idx, result in enumerate(doc_results):
                if result is None and best_seen[doc_idx][ref_idx] is not None:
                    doc_results[ref_idx] = (
                        self.gazetteer_name,
                        best_seen[doc_idx][ref_idx][1],
                    )

        return results

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def fit(
        self,
        texts: List[str],
        references: List[List[Tuple[int, int]]],
        referents: List[List[Tuple[str, str]]],
        output_path: Union[str, Path],
        epochs: int = 2,
        batch_size: int = 8,
        learning_rate: float = 2e-5,
        head_learning_rate: float = 1e-4,
        warmup_ratio: float = 0.1,
        max_negatives: int = 15,
        temperature: float = 0.05,
        gradient_accumulation_steps: int = 1,
        seed: int = 42,
        negative_search_methods: Tuple[str, ...] = ("exact", "phrase", "fuzzy"),
        in_batch_negatives: bool = True,
    ) -> None:
        """
        Fine-tune the span encoder with InfoNCE over same-name hard negatives.

        For each annotated mention, candidates retrieved by the gazetteer's
        search ladder for its surface form serve as hard negatives (the gold
        feature is the positive). Optionally, all candidates of the other
        mentions in the batch act as additional in-batch negatives. The loss
        is a cross-entropy over cosine similarities between the mention span
        embedding and the candidate embeddings.

        Args:
            texts: List of document text strings
            references: List of lists of (start, end) position tuples
            referents: List of lists of (gazetteer_name, identifier) tuples
            output_path: Directory path to save the fine-tuned model
            epochs: Number of training epochs
            batch_size: Number of mentions per optimization step
            learning_rate: Learning rate for the encoder backbone
            head_learning_rate: Learning rate for the projection head
            warmup_ratio: Warmup ratio for the learning rate scheduler
            max_negatives: Maximum number of same-name negatives per mention
            temperature: Softmax temperature for the InfoNCE loss
            gradient_accumulation_steps: Steps to accumulate gradients over
            seed: Random seed for shuffling and negative sampling
            negative_search_methods: Search methods used to mine hard negatives
                (mirrors the inference-time candidate ladder)
            in_batch_negatives: Whether other mentions' candidates in the batch
                serve as additional negatives
        """
        rng = random.Random(seed)

        print("Preparing training examples...")
        examples = self._prepare_training_examples(
            texts,
            references,
            referents,
            max_negatives,
            rng,
            negative_search_methods,
        )
        if not examples:
            raise ValueError(
                "No training examples found. Ensure documents contain references "
                "with referent annotations resolvable in the gazetteer."
            )
        print(f"Created {len(examples)} training examples")

        optimizer = torch.optim.AdamW(
            [
                {"params": self.encoder.parameters(), "lr": learning_rate},
                {"params": self.projection_head.parameters(), "lr": head_learning_rate},
            ],
            weight_decay=0.01,
        )
        steps_per_epoch = (len(examples) + batch_size - 1) // batch_size
        total_steps = max(
            steps_per_epoch * epochs // gradient_accumulation_steps, 1
        )
        warmup_steps = int(total_steps * warmup_ratio)
        scheduler = torch.optim.lr_scheduler.LambdaLR(
            optimizer,
            lambda step: (
                step / max(warmup_steps, 1)
                if step < warmup_steps
                else max(
                    0.0,
                    (total_steps - step) / max(total_steps - warmup_steps, 1),
                )
            ),
        )

        autocast_dtype = (
            torch.bfloat16
            if self.device.type == "cuda" and torch.cuda.is_bf16_supported()
            else torch.float32
        )

        self.encoder.train()
        self.projection_head.train()
        self.encoder.gradient_checkpointing_enable()

        step_count = 0
        for epoch in range(epochs):
            rng.shuffle(examples)
            epoch_loss, epoch_batches = 0.0, 0
            optimizer.zero_grad()

            for batch_start in range(0, len(examples), batch_size):
                batch = examples[batch_start : batch_start + batch_size]
                with torch.autocast(
                    device_type=self.device.type, dtype=autocast_dtype
                ):
                    loss = self._training_step(
                        batch, temperature, in_batch_negatives
                    )
                (loss / gradient_accumulation_steps).backward()

                if (
                    (batch_start // batch_size) + 1
                ) % gradient_accumulation_steps == 0:
                    torch.nn.utils.clip_grad_norm_(
                        list(self.encoder.parameters())
                        + list(self.projection_head.parameters()),
                        1.0,
                    )
                    optimizer.step()
                    scheduler.step()
                    optimizer.zero_grad()
                    step_count += 1

                epoch_loss += loss.item()
                epoch_batches += 1
                if epoch_batches % 50 == 0:
                    print(
                        f"epoch {epoch + 1}/{epochs} "
                        f"batch {epoch_batches}/{steps_per_epoch} "
                        f"loss {epoch_loss / epoch_batches:.4f}"
                    )

            print(
                f"Epoch {epoch + 1}/{epochs} finished, "
                f"mean loss {epoch_loss / max(epoch_batches, 1):.4f}"
            )

        self.encoder.gradient_checkpointing_disable()
        self.encoder.eval()
        self.projection_head.eval()

        # Invalidate any embeddings computed with the previous weights
        self.candidate_embeddings.clear()

        self.save(output_path)
        print(f"Model fine-tuning completed and saved to: {output_path}")

    def _prepare_training_examples(
        self,
        texts: List[str],
        references: List[List[Tuple[int, int]]],
        referents: List[List[Tuple[str, str]]],
        max_negatives: int,
        rng: random.Random,
        negative_search_methods: Tuple[str, ...] = ("exact",),
    ) -> List[dict]:
        """
        Build training examples with token windows and candidate serializations.

        Each example contains the mention's token window (input ids and span
        indices) plus serialized strings for the gold candidate and sampled
        same-name negatives.
        """
        examples = []
        search_cache: Dict[str, list] = {}
        serialization_cache: Dict[int, Tuple[str, str]] = {}

        def serialize(candidate: "Feature") -> Tuple[str, str]:
            if candidate.id not in serialization_cache:
                serialization_cache[candidate.id] = self._serialize_candidate(
                    candidate
                )
            return serialization_cache[candidate.id]

        for text, doc_references, doc_referents in zip(texts, references, referents):
            encoding = self.tokenizer(
                text,
                add_special_tokens=True,
                return_offsets_mapping=True,
                truncation=False,
            )
            for (start, end), referent in zip(doc_references, doc_referents):
                if referent is None:
                    continue
                _, identifier = referent
                if not identifier:
                    continue

                gold = self.gazetteer.find(identifier)
                if gold is None:
                    continue

                window_ids, first, last = self._mention_token_window(
                    encoding["input_ids"],
                    encoding["offset_mapping"],
                    start,
                    end,
                    self.max_context_tokens,
                )
                if window_ids is None:
                    continue

                surface = text[start:end]
                if surface not in search_cache:
                    seen_ids = set()
                    candidates = []
                    for method in negative_search_methods:
                        for candidate in self.gazetteer.search(surface, method):
                            if candidate.id not in seen_ids:
                                seen_ids.add(candidate.id)
                                candidates.append(candidate)
                    search_cache[surface] = candidates
                negatives = [
                    c
                    for c in search_cache[surface]
                    if c.location_id_value != identifier
                ]
                if len(negatives) > max_negatives:
                    negatives = rng.sample(negatives, max_negatives)

                examples.append(
                    {
                        "input_ids": window_ids,
                        "span": (first, last),
                        "gold": serialize(gold),
                        "gold_id": identifier,
                        "negatives": [serialize(c) for c in negatives],
                        "negative_ids": [c.location_id_value for c in negatives],
                    }
                )
        return examples

    def _training_step(
        self,
        batch: List[dict],
        temperature: float,
        in_batch_negatives: bool = True,
    ) -> torch.Tensor:
        """
        Compute the InfoNCE loss for a batch of training examples.

        With in_batch_negatives, each mention is scored against every candidate
        in the batch (its own and other mentions'), excluding candidates that
        share its gold identity; otherwise only against its own candidate set.
        """
        pad_id = self.tokenizer.pad_token_id

        # Encode mention windows
        max_len = max(len(e["input_ids"]) for e in batch)
        input_ids = torch.full(
            (len(batch), max_len), pad_id, dtype=torch.long, device=self.device
        )
        attention_mask = torch.zeros(
            (len(batch), max_len), dtype=torch.long, device=self.device
        )
        for i, example in enumerate(batch):
            ids = example["input_ids"]
            input_ids[i, : len(ids)] = torch.tensor(ids, device=self.device)
            attention_mask[i, : len(ids)] = 1

        hidden_states = self.encoder(
            input_ids=input_ids, attention_mask=attention_mask
        ).last_hidden_state
        mention_embeddings = self._pool_spans(
            hidden_states,
            attention_mask,
            [[example["span"]] for example in batch],
        )

        # Encode all candidate strings of the batch in one pass
        candidate_serializations: List[Tuple[str, str]] = []
        candidate_ids: List[str] = []
        gold_positions: List[int] = []
        candidate_slices: List[Tuple[int, int]] = []
        for example in batch:
            gold_positions.append(len(candidate_serializations))
            slice_start = len(candidate_serializations)
            candidate_serializations.append(example["gold"])
            candidate_ids.append(example["gold_id"])
            candidate_serializations.extend(example["negatives"])
            candidate_ids.extend(example["negative_ids"])
            candidate_slices.append(
                (slice_start, len(candidate_serializations))
            )

        candidate_embeddings = self._encode_candidates_trainable(
            candidate_serializations
        )

        if in_batch_negatives:
            # Score each mention against every candidate in the batch, masking
            # out other candidates that share the mention's gold identity
            logits = (mention_embeddings @ candidate_embeddings.T) / temperature
            mask = torch.zeros_like(logits, dtype=torch.bool)
            for i, example in enumerate(batch):
                for j, candidate_id in enumerate(candidate_ids):
                    if candidate_id == example["gold_id"] and j != gold_positions[i]:
                        mask[i, j] = True
            logits = logits.masked_fill(mask, float("-inf"))
            targets = torch.tensor(
                gold_positions, dtype=torch.long, device=self.device
            )
            return F.cross_entropy(logits, targets)

        # InfoNCE per mention over its own candidate set only (gold first)
        losses = []
        for i, (slice_start, slice_end) in enumerate(candidate_slices):
            logits = (
                mention_embeddings[i : i + 1]
                @ candidate_embeddings[slice_start:slice_end].T
            ) / temperature
            target = torch.zeros(1, dtype=torch.long, device=self.device)
            losses.append(F.cross_entropy(logits, target))
        return torch.stack(losses).mean()

    def _encode_candidates_trainable(
        self, serializations: List[Tuple[str, str]]
    ) -> torch.Tensor:
        """Encode candidate strings with gradients enabled (training path)."""
        texts = [s for s, _ in serializations]
        encodings = self.tokenizer(
            texts,
            add_special_tokens=True,
            return_offsets_mapping=True,
            padding=True,
            truncation=True,
            max_length=self.max_context_tokens,
            return_tensors="pt",
        )
        offsets = encodings.pop("offset_mapping")
        encodings = {k: v.to(self.device) for k, v in encodings.items()}

        token_spans: List[List[Tuple[int, int]]] = []
        for item_idx, (text, name) in enumerate(serializations):
            span = None
            if name:
                span = self._char_span_to_token_span(
                    offsets[item_idx].tolist(), 0, len(name)
                )
            if span is None:
                non_special = [
                    i for i, (s, e) in enumerate(offsets[item_idx].tolist()) if e > s
                ]
                span = (non_special[0], non_special[-1]) if non_special else (0, 0)
            token_spans.append([span])

        hidden_states = self.encoder(**encodings).last_hidden_state
        return self._pool_spans(
            hidden_states, encodings["attention_mask"], token_spans
        )
