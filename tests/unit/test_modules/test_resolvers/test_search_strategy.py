"""
Tests for the resolver's tiered search strategy.

The resolver widens its gazetteer search in tiers, trying the most restrictive
method first and skipping the exact method once the search has widened. These
pin that ordering, since getting it wrong still resolves most references while
quietly doing far more or far less work than intended.
"""

from unittest.mock import Mock, patch

import pytest


@pytest.fixture
def resolver():
    """A resolver with every external dependency stubbed out."""
    with (
        patch("geoparser.modules.resolvers.sentencetransformer.Gazetteer"),
        patch("geoparser.modules.resolvers.sentencetransformer.SentenceTransformer"),
        patch(
            "geoparser.modules.resolvers.sentencetransformer.AutoTokenizer.from_pretrained"
        ),
        patch("geoparser.modules.resolvers.sentencetransformer.spacy.load"),
    ):
        from geoparser.modules.resolvers.sentencetransformer import (
            SentenceTransformerResolver,
        )

        return SentenceTransformerResolver()


@pytest.mark.unit
class TestSearchTier:
    """Which search methods a tier runs, and in what order."""

    @staticmethod
    def _run(resolver, tiers, results):
        """Run one tier, recording the (method, tiers) of each search."""
        calls = []
        with patch.object(
            resolver,
            "_search_once",
            side_effect=lambda *a: calls.append((a[-2], a[-1])),
        ):
            resolver._search_tier([], [], [], [], results, tiers)
        return calls

    def test_first_tier_tries_every_method_in_order(self, resolver):
        """Nothing resolves, so all four methods run, most restrictive first."""
        # Act
        calls = self._run(resolver, tiers=1, results=[[None]])

        # Assert
        assert [method for method, _ in calls] == [
            "exact",
            "phrase",
            "partial",
            "fuzzy",
        ]

    def test_later_tiers_skip_the_exact_method_but_run_the_rest(self, resolver):
        """
        Widening the search cannot make an exact match appear.

        Skipping must be a `continue`: a `break` here would abandon the tier
        entirely and never try the looser methods.
        """
        # Act
        calls = self._run(resolver, tiers=2, results=[[None]])

        # Assert
        assert [method for method, _ in calls] == ["phrase", "partial", "fuzzy"]

    def test_passes_the_tier_through_to_each_search(self, resolver):
        """Every search in a tier is told which tier it belongs to."""
        # Act
        calls = self._run(resolver, tiers=3, results=[[None]])

        # Assert
        assert {tier for _, tier in calls} == {3}

    def test_stops_as_soon_as_everything_is_resolved(self, resolver):
        """A tier does not keep searching once no reference is left."""
        # Arrange - already resolved, so the first search ends the tier
        results = [[("geonames", "1")]]

        # Act
        calls = self._run(resolver, tiers=1, results=results)

        # Assert
        assert [method for method, _ in calls] == ["exact"]


@pytest.mark.unit
class TestAllResolved:
    """The early-exit predicate."""

    def test_true_when_every_reference_has_a_referent(self, resolver):
        assert resolver._all_resolved([[("g", "1")], [("g", "2")]]) is True

    def test_false_when_any_reference_is_still_unresolved(self, resolver):
        assert resolver._all_resolved([[("g", "1")], [None]]) is False

    def test_true_for_a_document_with_no_references(self, resolver):
        assert resolver._all_resolved([[]]) is True


@pytest.mark.unit
class TestUnresolvedCandidateLists:
    """Selecting the candidate lists still needing work."""

    def test_returns_only_the_lists_of_unresolved_references(self, resolver):
        """Resolved references are skipped."""
        # Arrange
        candidates = [[["a"], ["b"]], [["c"]]]
        results = [[None, ("g", "1")], [None]]

        # Act
        pending = resolver._unresolved_candidate_lists(candidates, results)

        # Assert
        assert pending == [["a"], ["c"]]

    def test_rejects_a_document_count_mismatch(self, resolver):
        """
        Candidates and results must describe the same documents.

        Zipping these leniently would silently drop a document's references
        rather than reporting that the two structures disagree.
        """
        # Act & Assert
        with pytest.raises(ValueError):
            resolver._unresolved_candidate_lists([[["a"]], [["b"]]], [[None]])

    def test_rejects_a_reference_count_mismatch_inside_a_document(self, resolver):
        """The same applies within one document."""
        # Act & Assert
        with pytest.raises(ValueError):
            resolver._unresolved_candidate_lists([[["a"], ["b"]]], [[None]])


@pytest.mark.unit
class TestMergeCandidates:
    """Adding newly found candidates to a reference."""

    def test_appends_only_candidates_not_already_present(self, resolver):
        """Duplicates by id are not added twice."""
        # Arrange
        existing = [Mock(id=1)]
        found = [Mock(id=1), Mock(id=2)]

        # Act
        resolver._merge_candidates(existing, found)

        # Assert
        assert [c.id for c in existing] == [1, 2]

    def test_keeps_the_order_new_candidates_arrived_in(self, resolver):
        """Newly found candidates are appended in gazetteer order."""
        # Arrange
        existing = []

        # Act
        resolver._merge_candidates(existing, [Mock(id=3), Mock(id=1), Mock(id=2)])

        # Assert
        assert [c.id for c in existing] == [3, 1, 2]


@pytest.mark.unit
class TestEncode:
    """How a batch of strings is handed to the encoder."""

    def test_asks_for_tensors(self, resolver):
        """Callers do tensor arithmetic on the result, so it must be tensors."""
        # Arrange
        resolver.transformer.encode = Mock(return_value="embeddings")

        # Act
        returned = resolver._encode(["a", "b"])

        # Assert
        assert returned == "embeddings"
        assert resolver.transformer.encode.call_args.args[0] == ["a", "b"]
        assert resolver.transformer.encode.call_args.kwargs["convert_to_tensor"] is True


@pytest.mark.unit
class TestEvaluateDocument:
    """Assigning referents to one document's references."""

    @staticmethod
    def _evaluate(resolver, contexts, candidates, results, best="referent"):
        """Run _evaluate_document with _best_referent stubbed."""
        seen = []

        def _best(context, candidate_list, min_similarity):
            seen.append(context)
            return ("geonames", best) if best else None

        with patch.object(resolver, "_best_referent", side_effect=_best):
            resolver._evaluate_document(contexts, candidates, results, 0.5)
        return seen

    def test_assigns_the_best_referent_to_an_unresolved_reference(self, resolver):
        """A reference with candidates gets the winner written back."""
        # Arrange
        results = [None]

        # Act
        self._evaluate(resolver, ["ctx"], [["cand"]], results)

        # Assert
        assert results == [("geonames", "referent")]

    def test_leaves_a_reference_alone_when_nothing_is_similar_enough(self, resolver):
        """No candidate above the threshold means no referent."""
        # Arrange
        results = [None]

        # Act
        self._evaluate(resolver, ["ctx"], [["cand"]], results, best=None)

        # Assert
        assert results == [None]

    def test_skips_references_that_are_already_resolved(self, resolver):
        """Work already done is not repeated or overwritten."""
        # Arrange
        results = [("geonames", "kept")]

        # Act
        seen = self._evaluate(resolver, ["ctx"], [["cand"]], results)

        # Assert
        assert seen == []
        assert results == [("geonames", "kept")]

    def test_skips_references_with_no_candidates_to_rank(self, resolver):
        """There is nothing to choose between, so nothing is ranked."""
        # Arrange
        results = [None]

        # Act
        seen = self._evaluate(resolver, ["ctx"], [[]], results)

        # Assert
        assert seen == []
        assert results == [None]

    def test_keeps_going_past_a_skipped_reference(self, resolver):
        """
        Skipping one reference must not abandon the rest of the document.

        A `break` here would leave every later reference unresolved whenever
        an earlier one happened to be done already.
        """
        # Arrange - first is resolved, second still needs a referent
        results = [("geonames", "kept"), None]

        # Act
        self._evaluate(resolver, ["a", "b"], [["cand"], ["cand"]], results)

        # Assert
        assert results == [("geonames", "kept"), ("geonames", "referent")]

    def test_rejects_contexts_candidates_and_results_of_different_lengths(
        self, resolver
    ):
        """The three per-reference lists must describe the same references."""
        # Act & Assert
        with (
            patch.object(resolver, "_best_referent", return_value=None),
            pytest.raises(ValueError),
        ):
            resolver._evaluate_document(["a", "b"], [["cand"]], [None], 0.5)


@pytest.mark.unit
class TestGatherCandidates:
    """Asking the gazetteer for candidates for unresolved references."""

    def test_searches_for_each_reference_substring(self, resolver):
        """
        The gazetteer is asked about the reference text, not the document.

        The slice, the method and the tier all come straight from the caller;
        searching the whole document, or with the wrong method, would return
        candidates for something other than the reference in hand.
        """
        # Arrange
        resolver.gazetteer.search = Mock(return_value=[])
        candidates = [[[], []]]

        # Act
        resolver._gather_candidates(
            ["Paris and Berlin"],
            [[(0, 5), (10, 16)]],
            candidates,
            [[None, None]],
            "phrase",
            3,
        )

        # Assert
        assert [c.args for c in resolver.gazetteer.search.call_args_list] == [
            ("Paris", "phrase"),
            ("Berlin", "phrase"),
        ]
        assert {
            c.kwargs["tiers"] for c in resolver.gazetteer.search.call_args_list
        } == {3}

    def test_skips_references_that_are_already_resolved(self, resolver):
        """
        A resolved reference needs no more candidates.

        Skipping must continue to the next reference: breaking would abandon
        every later reference in the document.
        """
        # Arrange
        resolver.gazetteer.search = Mock(return_value=[])
        candidates = [[[], []]]

        # Act
        resolver._gather_candidates(
            ["Paris and Berlin"],
            [[(0, 5), (10, 16)]],
            candidates,
            [[("geonames", "1"), None]],
            "exact",
            1,
        )

        # Assert - only the unresolved second reference was searched
        assert [c.args[0] for c in resolver.gazetteer.search.call_args_list] == [
            "Berlin"
        ]

    def test_stores_found_candidates_against_their_reference(self, resolver):
        """Candidates land in the slot belonging to the reference searched."""
        # Arrange
        found = Mock(id=7)
        resolver.gazetteer.search = Mock(return_value=[found])
        candidates = [[[]]]

        # Act
        resolver._gather_candidates(
            ["Paris"], [[(0, 5)]], candidates, [[None]], "exact", 1
        )

        # Assert
        assert candidates == [[[found]]]

    def test_rejects_documents_and_references_of_different_lengths(self, resolver):
        """The parallel structures must agree on how many documents there are."""
        # Act & Assert
        with pytest.raises(ValueError):
            resolver._gather_candidates(
                ["a", "b"], [[(0, 1)]], [[[]]], [[None]], "exact", 1
            )


@pytest.mark.unit
class TestPredictTiers:
    """How many tiers predict works through, and what it returns."""

    @staticmethod
    def _predict(resolver, max_tiers, resolve_after=None):
        """Run predict over one reference, recording the tiers attempted."""
        resolver.max_tiers = max_tiers
        tiers_tried = []

        def _search_tier(texts, references, contexts, candidates, results, tiers):
            tiers_tried.append(tiers)
            if resolve_after is not None and tiers >= resolve_after:
                results[0][0] = ("geonames", "1")

        with (
            patch.object(resolver, "_extract_contexts", return_value=[["ctx"]]),
            patch.object(resolver, "_embed_contexts"),
            patch.object(resolver, "_search_tier", side_effect=_search_tier),
        ):
            returned = resolver.predict(["Paris"], [[(0, 5)]])
        return tiers_tried, returned

    def test_works_through_every_tier_when_nothing_resolves(self, resolver):
        """Tiers run from one up to max_tiers inclusive."""
        # Act
        tiers_tried, _ = self._predict(resolver, max_tiers=3)

        # Assert
        assert tiers_tried == [1, 2, 3]

    def test_stops_at_the_first_tier_that_resolves_everything(self, resolver):
        """No further widening once every reference has a referent."""
        # Act
        tiers_tried, _ = self._predict(resolver, max_tiers=3, resolve_after=1)

        # Assert
        assert tiers_tried == [1]

    def test_returns_the_results_it_filled_in(self, resolver):
        """
        predict hands back the referents, one slot per reference.

        Leaving the loop with a bare return instead of a break would hand the
        caller None while still having done all the work.
        """
        # Act
        _, returned = self._predict(resolver, max_tiers=2, resolve_after=1)

        # Assert
        assert returned == [[("geonames", "1")]]

    def test_returns_nothing_for_no_texts(self, resolver):
        """No documents means no work and an empty result."""
        # Act & Assert
        assert resolver.predict([], []) == []


@pytest.mark.unit
class TestSearchOnce:
    """One gather/embed/evaluate pass."""

    def test_passes_the_method_and_tier_on_to_the_gazetteer_search(self, resolver):
        """_search_once is a relay; the search parameters must survive it."""
        # Arrange
        with (
            patch.object(resolver, "_gather_candidates") as gather,
            patch.object(resolver, "_embed_candidates"),
            patch.object(resolver, "_evaluate_candidates"),
        ):
            # Act
            resolver._search_once(
                ["t"], [[(0, 1)]], [["c"]], [[[]]], [[None]], "fuzzy", 2
            )

        # Assert
        assert gather.call_args.args[-2:] == ("fuzzy", 2)

    def test_evaluates_against_the_configured_similarity_threshold(self, resolver):
        """The resolver's own threshold decides what counts as a match."""
        # Arrange
        resolver.min_similarity = 0.75
        with (
            patch.object(resolver, "_gather_candidates"),
            patch.object(resolver, "_embed_candidates"),
            patch.object(resolver, "_evaluate_candidates") as evaluate,
        ):
            # Act
            resolver._search_once(
                ["t"], [[(0, 1)]], [["c"]], [[[]]], [[None]], "exact", 1
            )

        # Assert
        assert evaluate.call_args.args[-1] == 0.75
