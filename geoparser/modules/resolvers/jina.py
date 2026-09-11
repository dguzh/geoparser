"""
Toponym resolution with the Jina v5 embedding model and a v3.5 reranker.

This resolver keeps the tiered gazetteer search of
:class:`~geoparser.modules.resolvers.sentencetransformer.SentenceTransformerResolver`
and changes how a referent is chosen from the candidates it finds:

- **Asymmetric embeddings.** ``jina-embeddings-v5`` has separate prompts for
  the query side and the document side of a retrieval pair. A reference's
  context is a query; a candidate's description is a document. Embedding both
  under the same prompt loses most of the benefit of the model.
- **Two-stage ranking.** The embedding comparison is cheap but sees each side
  in isolation. It is used to shortlist, and ``jina-reranker-v3.5`` -- a cross
  encoder, which reads the context and the candidate together -- picks the
  winner from that shortlist.
"""

import typing as t

from transformers import AutoModel

from geoparser.modules.resolvers.sentencetransformer import SentenceTransformerResolver

if t.TYPE_CHECKING:
    import torch

    from geoparser.gazetteer.feature import Feature

# The prompt each kind of text is embedded under. Both sides of a retrieval
# pair use the retrieval adapter; only the prompt differs.
_ENCODE_TASK = "retrieval"
_ROLE_PROMPTS = {"context": "query", "candidate": "document"}


class JinaResolver(SentenceTransformerResolver):
    """
    A resolver that embeds with Jina v5 and re-scores with a Jina reranker.

    Candidate retrieval, context windowing and the tier logic are inherited
    unchanged; only the encoding prompts and the final choice of referent
    differ from the parent.
    """

    NAME = "JinaResolver"

    DEFAULT_MODEL_NAME = "jinaai/jina-embeddings-v5-text-small"
    DEFAULT_RERANKER_NAME = "jinaai/jina-reranker-v3.5"

    # How many of the best-embedded candidates the cross encoder sees. The
    # cross encoder is far more expensive per candidate than the embedding
    # comparison, so the shortlist is what keeps resolution affordable.
    DEFAULT_RERANK_TOP_K = 20

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL_NAME,
        reranker_name: str = DEFAULT_RERANKER_NAME,
        rerank_top_k: int = DEFAULT_RERANK_TOP_K,
        **kwargs,
    ):
        """
        Initialize the Jina resolver.

        Args:
            model_name: HuggingFace checkpoint for the embedding model
            reranker_name: HuggingFace checkpoint for the cross encoder
            rerank_top_k: How many of the best-embedded candidates to rerank
            **kwargs: Passed to
                :class:`~geoparser.modules.resolvers.sentencetransformer.SentenceTransformerResolver`
                (``gazetteer_name``, ``min_similarity``, ``max_tiers``,
                ``attribute_map``)

        Raises:
            ValueError: If ``rerank_top_k`` is less than one, which would
                leave the cross encoder nothing to rank
        """
        if rerank_top_k < 1:
            # pragma: no mutate start - wording only; a test pins the type and
            # that the message names the parameter.
            raise ValueError(
                f"rerank_top_k must be at least 1, got {rerank_top_k}: the "
                "reranker needs at least one candidate to choose from."
            )
            # pragma: no mutate end

        self.reranker_name = reranker_name
        self.rerank_top_k = rerank_top_k

        super().__init__(
            model_name=model_name,
            reranker_name=reranker_name,
            rerank_top_k=rerank_top_k,
            **kwargs,
        )

        self.reranker = AutoModel.from_pretrained(
            reranker_name, dtype="auto", trust_remote_code=True
        )
        self.reranker.eval()

    def _load_transformer(self, model_name: str, **kwargs):
        """
        Load the embedding model, allowing its bundled modelling code to run.

        Args:
            model_name: HuggingFace checkpoint for the embedding model
            **kwargs: Extra arguments for the SentenceTransformer constructor

        Returns:
            The loaded SentenceTransformer
        """
        return super()._load_transformer(model_name, trust_remote_code=True, **kwargs)

    def _load_tokenizer(self, model_name: str, **kwargs):
        """
        Load the tokenizer, allowing its bundled code to run.

        Args:
            model_name: HuggingFace checkpoint to load the tokenizer of
            **kwargs: Extra arguments for ``AutoTokenizer.from_pretrained``

        Returns:
            The loaded tokenizer
        """
        return super()._load_tokenizer(model_name, trust_remote_code=True, **kwargs)

    def _encode(self, texts: list[str], role: str) -> "torch.Tensor":
        """
        Embed a batch of strings under the prompt for their role.

        Args:
            texts: Strings to embed
            role: ``"context"`` for reference contexts, ``"candidate"`` for
                  candidate descriptions

        Returns:
            One embedding per input string, in the same order

        Raises:
            ValueError: If the role is not one of the two retrieval roles
        """
        if role not in _ROLE_PROMPTS:
            # pragma: no mutate start - wording only; a test pins the type and
            # that the message names the parameter.
            raise ValueError(
                f"Unknown encoding role {role!r}; expected one of "
                f"{sorted(_ROLE_PROMPTS)}."
            )
            # pragma: no mutate end

        return self.transformer.encode(
            texts,
            convert_to_tensor=True,
            task=_ENCODE_TASK,
            prompt_name=_ROLE_PROMPTS[role],
        )

    def _best_referent(
        self,
        context: str,
        candidate_list: list["Feature"],
        min_similarity: float,
    ) -> tuple[str, str] | None:
        """
        Pick a referent by shortlisting on embeddings and reranking.

        Args:
            context: The reference's context string
            candidate_list: Candidates to rank, all already embedded
            min_similarity: Similarity the best candidate must reach

        Returns:
            A (gazetteer_name, identifier) pair, or None when no candidate is
            similar enough
        """
        similarities = self._calculate_similarities(
            self.context_embeddings[context],
            [self.candidate_embeddings[candidate.id] for candidate in candidate_list],
        )
        if not similarities:
            return None

        shortlist = self._shortlist(candidate_list, similarities)
        if max(similarities) < min_similarity:
            return None

        return self.gazetteer_name, self._reranked(context, shortlist).identifier

    def _shortlist(
        self, candidate_list: list["Feature"], similarities: list[float]
    ) -> list["Feature"]:
        """
        The best-embedded candidates, most similar first.

        Args:
            candidate_list: Candidates in gazetteer order
            similarities: One embedding similarity per candidate

        Returns:
            At most ``rerank_top_k`` candidates, best first
        """
        ranked = sorted(
            range(len(candidate_list)),
            key=lambda index: similarities[index],
            reverse=True,
        )
        return [candidate_list[index] for index in ranked[: self.rerank_top_k]]

    def _reranked(self, context: str, shortlist: list["Feature"]) -> "Feature":
        """
        The shortlisted candidate the cross encoder scores highest.

        Args:
            context: The reference's context string
            shortlist: Candidates to re-score, best-embedded first

        Returns:
            The winning candidate, falling back to the best-embedded one when
            the reranker returns no ranking at all
        """
        descriptions = [
            self._generate_description(candidate) for candidate in shortlist
        ]
        ranking = self.reranker.rerank(context, descriptions, top_n=1)
        if not ranking:
            return shortlist[0]
        return shortlist[ranking[0]["index"]]
