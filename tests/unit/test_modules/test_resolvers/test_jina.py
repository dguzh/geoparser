"""
Unit tests for the Jina resolver.

The Jina resolver reuses the tiered gazetteer search of its parent and changes
two things: the embedding model is asymmetric, so contexts and candidate
descriptions must be encoded under different prompts, and the top of the
embedding ranking is re-scored by a cross-encoder before a referent is
chosen. Both are invisible in the returned type and easy to get subtly wrong,
which is what these pin.
"""

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
import torch

from geoparser.modules.resolvers.jina import JinaResolver

MODULE = "geoparser.modules.resolvers.jina"
PARENT = "geoparser.modules.resolvers.sentencetransformer"


def _feature(feature_id: int, identifier: str, name: str):
    """A stand-in gazetteer feature with a name to describe it by."""
    return SimpleNamespace(id=feature_id, identifier=identifier, data={"name": name})


@pytest.fixture
def patched():
    """Every model the resolver loads, replaced by a Mock."""
    with (
        patch(f"{PARENT}.Gazetteer"),
        patch(f"{PARENT}.SentenceTransformer") as transformer,
        patch(f"{PARENT}.AutoTokenizer.from_pretrained"),
        patch(f"{PARENT}.spacy.load"),
        patch(f"{MODULE}.AutoModel.from_pretrained") as reranker,
    ):
        yield SimpleNamespace(
            transformer=transformer,
            reranker=reranker,
        )


@pytest.fixture
def resolver(patched):
    """A Jina resolver with a custom attribute map, so no gazetteer is needed."""
    return JinaResolver(attribute_map={"name": "name", "type": "type"})


@pytest.mark.unit
class TestInitialization:
    """Which checkpoints are loaded, and what ends up in the config."""

    def test_defaults_to_the_jina_embedding_and_reranker_checkpoints(
        self, patched, resolver
    ):
        """Both defaults are the v5 small embedder and the v3.5 reranker."""
        # Assert
        assert resolver.model_name == "jinaai/jina-embeddings-v5-text-small"
        assert resolver.reranker_name == "jinaai/jina-reranker-v3.5"
        patched.transformer.assert_called_once_with(
            "jinaai/jina-embeddings-v5-text-small", trust_remote_code=True
        )

    def test_loads_the_reranker_with_remote_code_enabled(self, patched, resolver):
        """The reranker ships its own modelling code, so it must be trusted."""
        # Assert
        patched.reranker.assert_called_once_with(
            "jinaai/jina-reranker-v3.5", dtype="auto", trust_remote_code=True
        )

    def test_puts_the_reranker_in_evaluation_mode(self, patched, resolver):
        """Inference only: dropout and the like stay off."""
        # Assert
        patched.reranker.return_value.eval.assert_called_once_with()

    def test_the_reranker_is_part_of_the_module_identity(self, patched):
        """
        Swapping the reranker changes the module id.

        Two resolvers that embed identically but re-score differently produce
        different referents, so they must not share an id.
        """
        # Arrange
        attribute_map = {"name": "name", "type": "type"}

        # Act
        default = JinaResolver(attribute_map=attribute_map)
        other = JinaResolver(reranker_name="jinaai/other", attribute_map=attribute_map)

        # Assert
        assert other.config["reranker_name"] == "jinaai/other"
        assert other.id != default.id

    def test_the_shortlist_size_is_part_of_the_module_identity(self, patched):
        """How many candidates reach the reranker also changes the outcome."""
        # Arrange
        attribute_map = {"name": "name", "type": "type"}

        # Act
        default = JinaResolver(attribute_map=attribute_map)
        wider = JinaResolver(rerank_top_k=50, attribute_map=attribute_map)

        # Assert
        assert wider.config["rerank_top_k"] == 50
        assert wider.id != default.id

    def test_rejects_a_shortlist_of_less_than_one(self, patched):
        """A reranker with nothing to rank cannot choose a referent."""
        # Act & Assert
        with pytest.raises(ValueError, match="rerank_top_k"):
            JinaResolver(rerank_top_k=0, attribute_map={"name": "name"})


@pytest.mark.unit
class TestAsymmetricEncoding:
    """The prompts under which the two kinds of text are embedded."""

    def test_contexts_are_embedded_as_queries(self, resolver):
        """A reference context is the query side of the retrieval pair."""
        # Act
        resolver._encode(["context text"], role="context")

        # Assert
        assert resolver.transformer.encode.call_args.kwargs["prompt_name"] == "query"

    def test_candidate_descriptions_are_embedded_as_documents(self, resolver):
        """A candidate description is the document side."""
        # Act
        resolver._encode(["Paris (city)"], role="candidate")

        # Assert
        assert resolver.transformer.encode.call_args.kwargs["prompt_name"] == "document"

    def test_both_sides_are_encoded_for_retrieval(self, resolver):
        """The retrieval task selects the right adapter for both roles."""
        # Act
        resolver._encode(["a"], role="context")
        resolver._encode(["b"], role="candidate")

        # Assert
        tasks = [
            call.kwargs["task"] for call in resolver.transformer.encode.call_args_list
        ]
        assert tasks == ["retrieval", "retrieval"]

    def test_an_unknown_role_is_rejected(self, resolver):
        """Only the two retrieval roles have a prompt."""
        # Act & Assert
        with pytest.raises(ValueError, match="role"):
            resolver._encode(["a"], role="something-else")


@pytest.mark.unit
class TestReranking:
    """Choosing a referent from the embedding shortlist."""

    @staticmethod
    def _prepare(resolver, candidates, similarities, ranking):
        """Wire up the embedding scores and the reranker's verdict."""
        resolver.context_embeddings["ctx"] = torch.zeros(2)
        for candidate in candidates:
            resolver.candidate_embeddings[candidate.id] = torch.zeros(2)
        resolver._calculate_similarities = Mock(return_value=similarities)
        resolver.reranker.rerank = Mock(return_value=ranking)

    def test_the_reranker_can_overturn_the_embedding_ranking(self, resolver):
        """
        The cross-encoder has the last word.

        The whole point of the second stage is that it sees the context and
        the candidate together; if the embedding order still decided, the
        reranker would be dead weight.
        """
        # Arrange
        candidates = [_feature(1, "A", "Paris"), _feature(2, "B", "Paris, Texas")]
        self._prepare(
            resolver,
            candidates,
            similarities=[0.9, 0.7],
            ranking=[{"index": 1, "relevance_score": 0.95}],
        )

        # Act
        referent = resolver._best_referent("ctx", candidates, 0.0)

        # Assert
        assert referent == (resolver.gazetteer_name, "B")

    def test_the_reranker_is_given_the_context_and_the_descriptions(self, resolver):
        """It scores the candidate descriptions against the context text."""
        # Arrange
        candidates = [_feature(1, "A", "Paris"), _feature(2, "B", "Berlin")]
        self._prepare(
            resolver,
            candidates,
            similarities=[0.9, 0.7],
            ranking=[{"index": 0, "relevance_score": 0.95}],
        )

        # Act
        resolver._best_referent("ctx", candidates, 0.0)

        # Assert
        resolver.reranker.rerank.assert_called_once_with(
            "ctx", ["Paris", "Berlin"], top_n=1
        )

    def test_only_the_best_embedded_candidates_are_reranked(self, resolver):
        """
        The shortlist is capped, in embedding-score order.

        The cross-encoder is quadratically more expensive than the embedding
        comparison, so it must see the most promising candidates rather than
        whichever the gazetteer happened to return first.
        """
        # Arrange
        resolver.rerank_top_k = 2
        candidates = [
            _feature(1, "A", "Alpha"),
            _feature(2, "B", "Beta"),
            _feature(3, "C", "Gamma"),
        ]
        self._prepare(
            resolver,
            candidates,
            similarities=[0.1, 0.9, 0.5],
            ranking=[{"index": 0, "relevance_score": 0.95}],
        )

        # Act
        referent = resolver._best_referent("ctx", candidates, 0.0)

        # Assert
        resolver.reranker.rerank.assert_called_once_with(
            "ctx", ["Beta", "Gamma"], top_n=1
        )
        assert referent == (resolver.gazetteer_name, "B")

    def test_a_candidate_below_the_similarity_threshold_is_not_resolved(self, resolver):
        """The embedding stage still gates on min_similarity."""
        # Arrange
        candidates = [_feature(1, "A", "Paris")]
        self._prepare(
            resolver,
            candidates,
            similarities=[0.2],
            ranking=[{"index": 0, "relevance_score": 0.95}],
        )

        # Act & Assert
        assert resolver._best_referent("ctx", candidates, 0.6) is None
        resolver.reranker.rerank.assert_not_called()

    def test_no_candidates_means_no_referent(self, resolver):
        """Nothing to rank is not an error."""
        # Arrange
        resolver.context_embeddings["ctx"] = torch.zeros(2)
        resolver._calculate_similarities = Mock(return_value=[])
        resolver.reranker.rerank = Mock()

        # Act & Assert
        assert resolver._best_referent("ctx", [], 0.0) is None
        resolver.reranker.rerank.assert_not_called()

    def test_an_empty_ranking_falls_back_to_the_embedding_choice(self, resolver):
        """
        If the reranker returns nothing, the embedding pick stands.

        Dropping the reference entirely would throw away a candidate the
        first stage was confident enough about to shortlist.
        """
        # Arrange
        candidates = [_feature(1, "A", "Paris"), _feature(2, "B", "Berlin")]
        self._prepare(resolver, candidates, similarities=[0.3, 0.9], ranking=[])

        # Act & Assert
        assert resolver._best_referent("ctx", candidates, 0.0) == (
            resolver.gazetteer_name,
            "B",
        )


@pytest.mark.unit
class TestModelLoading:
    """What reaches the two ``from_pretrained`` calls."""

    def test_the_tokenizer_is_loaded_for_the_embedding_checkpoint(self, patched):
        """Context sizing must use the tokenizer of the model that embeds."""
        # Arrange
        with patch(f"{PARENT}.AutoTokenizer.from_pretrained") as tokenizer:
            # Act
            JinaResolver(attribute_map={"name": "name"})

        # Assert
        tokenizer.assert_called_once_with(
            "jinaai/jina-embeddings-v5-text-small", trust_remote_code=True
        )

    def test_extra_loader_arguments_are_forwarded(self, resolver):
        """The hooks pass a caller's extras through to transformers."""
        # Arrange
        with patch(f"{PARENT}.AutoTokenizer.from_pretrained") as tokenizer:
            # Act
            resolver._load_tokenizer("some/model", revision="abc")

        # Assert
        tokenizer.assert_called_once_with(
            "some/model", trust_remote_code=True, revision="abc"
        )

    def test_extra_embedding_arguments_are_forwarded(self, patched, resolver):
        """The same holds for the embedding model's loader."""
        # Act
        resolver._load_transformer("some/model", device="cpu")

        # Assert
        assert patched.transformer.call_args.args == ("some/model",)
        assert patched.transformer.call_args.kwargs == {
            "trust_remote_code": True,
            "device": "cpu",
        }

    def test_resolver_parameters_reach_the_parent(self, patched):
        """
        Arguments meant for the parent are not swallowed by ``**kwargs``.

        Dropping them would silently reset the similarity threshold and the
        tier count to their defaults, which changes what resolves.
        """
        # Act
        resolver = JinaResolver(
            min_similarity=0.25, max_tiers=1, attribute_map={"name": "name"}
        )

        # Assert
        assert resolver.min_similarity == 0.25
        assert resolver.max_tiers == 1
        assert resolver.config["min_similarity"] == 0.25


@pytest.mark.unit
class TestShortlistSizeBoundary:
    """Where the ``rerank_top_k`` guard draws its line."""

    def test_a_shortlist_of_one_is_allowed(self, patched):
        """
        One candidate is enough for the reranker to confirm or reject.

        The guard rejects zero, not one: a shortlist of one is a legitimate,
        if unusual, way to run with the reranker almost disabled.
        """
        # Act
        resolver = JinaResolver(rerank_top_k=1, attribute_map={"name": "name"})

        # Assert
        assert resolver.rerank_top_k == 1

    def test_a_negative_shortlist_is_rejected(self, patched):
        """Below zero is rejected for the same reason as zero."""
        # Act & Assert
        with pytest.raises(ValueError, match="rerank_top_k"):
            JinaResolver(rerank_top_k=-1, attribute_map={"name": "name"})

    def test_the_configured_size_is_the_one_used(self, patched):
        """The value is stored, not just validated."""
        # Act
        resolver = JinaResolver(rerank_top_k=7, attribute_map={"name": "name"})

        # Assert
        assert resolver.rerank_top_k == 7


@pytest.mark.unit
class TestEncodeArguments:
    """What the embedding call is actually given."""

    def test_the_texts_are_passed_through(self, resolver):
        """The strings asked for are the strings embedded."""
        # Act
        resolver._encode(["one", "two"], role="context")

        # Assert
        assert resolver.transformer.encode.call_args.args == (["one", "two"],)

    def test_the_result_is_asked_for_as_a_tensor(self, resolver):
        """Callers do tensor arithmetic on what comes back."""
        # Act
        resolver._encode(["one"], role="context")

        # Assert
        assert resolver.transformer.encode.call_args.kwargs["convert_to_tensor"] is True

    def test_candidate_descriptions_are_embedded_under_the_document_prompt(
        self, resolver
    ):
        """
        The candidate side of the pipeline asks for the document prompt.

        This is the call the parent class makes on the resolver's behalf, so
        it is where a wrong role would actually reach the model.
        """
        # Arrange
        candidate = _feature(1, "A", "Paris")
        resolver._generate_description = Mock(return_value="Paris (city)")

        # Act
        resolver._embed_candidates([[[candidate]]], [[None]])

        # Assert
        assert resolver.transformer.encode.call_args.kwargs["prompt_name"] == "document"


@pytest.mark.unit
class TestSimilarityInputs:
    """Which embeddings the comparison is given."""

    def test_the_context_and_candidate_embeddings_are_compared(self, resolver):
        """
        Both sides come from the caches, keyed correctly.

        Handing the comparison the wrong tensors -- or none -- would rank
        candidates against something other than the reference's context.
        """
        # Arrange
        candidates = [_feature(1, "A", "Paris"), _feature(2, "B", "Berlin")]
        context_embedding = torch.tensor([1.0, 0.0])
        resolver.context_embeddings["ctx"] = context_embedding
        first, second = torch.tensor([1.0, 0.0]), torch.tensor([0.0, 1.0])
        resolver.candidate_embeddings[1] = first
        resolver.candidate_embeddings[2] = second
        resolver._calculate_similarities = Mock(return_value=[0.9, 0.1])
        resolver.reranker.rerank = Mock(return_value=[{"index": 0}])

        # Act
        resolver._best_referent("ctx", candidates, 0.0)

        # Assert
        passed_context, passed_candidates = (
            resolver._calculate_similarities.call_args.args
        )
        assert passed_context is context_embedding
        assert passed_candidates == [first, second]

    def test_a_candidate_exactly_at_the_threshold_is_accepted(self, resolver):
        """
        The threshold is inclusive.

        ``min_similarity`` reads as the similarity a candidate must reach, so
        reaching it exactly has to be enough.
        """
        # Arrange
        candidates = [_feature(1, "A", "Paris")]
        resolver.context_embeddings["ctx"] = torch.zeros(2)
        resolver.candidate_embeddings[1] = torch.zeros(2)
        resolver._calculate_similarities = Mock(return_value=[0.6])
        resolver.reranker.rerank = Mock(return_value=[{"index": 0}])

        # Act & Assert
        assert resolver._best_referent("ctx", candidates, 0.6) == (
            resolver.gazetteer_name,
            "A",
        )

    def test_reference_contexts_are_embedded_under_the_query_prompt(self, resolver):
        """
        The context side of the pipeline asks for the query prompt.

        As with the candidates above, this is the call the parent class makes
        on the resolver's behalf. Getting the two roles the wrong way round
        embeds every reference as though it were a gazetteer entry, which
        degrades ranking without failing anything.
        """
        # Act
        resolver._embed_contexts([["a reference context"]])

        # Assert
        assert resolver.transformer.encode.call_args.kwargs["prompt_name"] == "query"
