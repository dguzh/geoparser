"""
Integration tests for geoparser/modules/resolvers/manual.py

Tests ManualResolver with real database interactions.
"""

import pytest

from geoparser.modules.resolvers.manual import ManualResolver


@pytest.mark.integration
class TestManualResolverIntegration:
    """Integration tests for ManualResolver."""

    def test_creates_deterministic_id_from_label(self):
        """Test that ManualResolver generates deterministic ID from label."""
        # Arrange
        texts = ["Paris is beautiful."]
        references = [[(0, 5)]]
        referents = [[("geonames", "2988507")]]

        # Act
        resolver1 = ManualResolver(
            label="test_label",
            texts=texts,
            references=references,
            referents=referents,
        )
        resolver2 = ManualResolver(
            label="test_label",
            texts=texts,
            references=references,
            referents=referents,
        )

        # Assert
        assert resolver1.id == resolver2.id

    def test_different_labels_produce_different_ids(self):
        """Test that different labels produce different resolver IDs."""
        # Arrange
        texts = ["Paris is beautiful."]
        references = [[(0, 5)]]
        referents = [[("geonames", "2988507")]]

        # Act
        resolver1 = ManualResolver(
            label="label_a",
            texts=texts,
            references=references,
            referents=referents,
        )
        resolver2 = ManualResolver(
            label="label_b",
            texts=texts,
            references=references,
            referents=referents,
        )

        # Assert
        assert resolver1.id != resolver2.id

    def test_predicts_referent_for_single_reference(self):
        """Test that ManualResolver returns referent for a single reference."""
        # Arrange
        texts = ["New York is a major city."]
        references = [[(0, 8)]]
        referents = [[("geonames", "5128581")]]
        resolver = ManualResolver(
            label="test", texts=texts, references=references, referents=referents
        )

        # Act
        results = resolver.predict(texts, references)

        # Assert
        assert len(results) == 1
        assert len(results[0]) == 1
        assert results[0][0] == ("geonames", "5128581")

    def test_predicts_multiple_referents_in_document(self):
        """Test that ManualResolver handles multiple references in one document."""
        # Arrange
        texts = ["Paris and London are cities."]
        references = [[(0, 5), (10, 16)]]
        referents = [[("geonames", "2988507"), ("geonames", "2643743")]]
        resolver = ManualResolver(
            label="test", texts=texts, references=references, referents=referents
        )

        # Act
        results = resolver.predict(texts, references)

        # Assert
        assert len(results) == 1
        assert len(results[0]) == 2
        assert results[0][0] == ("geonames", "2988507")
        assert results[0][1] == ("geonames", "2643743")

    def test_predicts_referents_for_multiple_documents(self):
        """Test that ManualResolver handles multiple documents."""
        # Arrange
        texts = ["Berlin is in Germany.", "Tokyo is in Japan."]
        references = [[(0, 6)], [(0, 5)]]
        referents = [[("geonames", "2950159")], [("geonames", "1850144")]]
        resolver = ManualResolver(
            label="test", texts=texts, references=references, referents=referents
        )

        # Act
        results = resolver.predict(texts, references)

        # Assert
        assert len(results) == 2
        assert results[0] == [("geonames", "2950159")]
        assert results[1] == [("geonames", "1850144")]

    def test_returns_none_for_unannotated_document(self):
        """Test that ManualResolver returns None for references without annotations."""
        # Arrange
        texts = ["Paris is beautiful."]
        references = [[(0, 5)]]
        referents = [[("geonames", "2988507")]]
        resolver = ManualResolver(
            label="test", texts=texts, references=references, referents=referents
        )

        # Act - Query with different text
        results = resolver.predict(["London is great."], [[(0, 6)]])

        # Assert
        assert len(results) == 1
        assert results[0] == [None]

    def test_returns_none_for_unannotated_reference(self):
        """Test that ManualResolver returns None for specific references without annotations."""
        # Arrange
        texts = ["Paris and London are cities."]
        references = [[(0, 5)]]  # Only Paris annotated
        referents = [[("geonames", "2988507")]]
        resolver = ManualResolver(
            label="test", texts=texts, references=references, referents=referents
        )

        # Act - Query with both Paris and London
        results = resolver.predict(texts, [[(0, 5), (10, 16)]])

        # Assert
        assert len(results) == 1
        assert len(results[0]) == 2
        assert results[0][0] == ("geonames", "2988507")
        assert results[0][1] is None  # London not annotated

    def test_handles_empty_reference_list(self):
        """Test that ManualResolver handles documents with no references."""
        # Arrange
        texts = ["No locations here."]
        references = [[]]
        referents = [[]]
        resolver = ManualResolver(
            label="test", texts=texts, references=references, referents=referents
        )

        # Act
        results = resolver.predict(texts, references)

        # Assert
        assert len(results) == 1
        assert results[0] == []

    def test_exact_text_and_reference_matching(self):
        """Test that both text and reference positions must match exactly."""
        # Arrange
        texts = ["Paris is beautiful."]
        references = [[(0, 5)]]
        referents = [[("geonames", "2988507")]]
        resolver = ManualResolver(
            label="test", texts=texts, references=references, referents=referents
        )

        # Act - Same text but different reference position
        results = resolver.predict(["Paris is beautiful."], [[(0, 6)]])

        # Assert
        assert results[0] == [None]  # Different position, no match

    def test_mixed_annotated_and_unannotated_references(self):
        """Test that resolver handles mix of annotated and unannotated references."""
        # Arrange
        texts = ["Paris and London and Berlin"]
        references = [[(0, 5), (10, 16)]]  # Only Paris and London annotated
        referents = [[("geonames", "2988507"), ("geonames", "2643743")]]
        resolver = ManualResolver(
            label="test", texts=texts, references=references, referents=referents
        )

        # Act - Query with all three cities
        results = resolver.predict(texts, [[(0, 5), (10, 16), (21, 27)]])

        # Assert
        assert len(results[0]) == 3
        assert results[0][0] == ("geonames", "2988507")  # Paris - annotated
        assert results[0][1] == ("geonames", "2643743")  # London - annotated
        assert results[0][2] is None  # Berlin - not annotated

    def test_preserves_referent_order(self):
        """Test that referent order matches reference order."""
        # Arrange
        texts = ["A B C"]
        references = [[(2, 3), (4, 5), (0, 1)]]  # B, C, A
        referents = [[("gaz", "b"), ("gaz", "c"), ("gaz", "a")]]
        resolver = ManualResolver(
            label="test", texts=texts, references=references, referents=referents
        )

        # Act
        results = resolver.predict(texts, references)

        # Assert
        assert results[0] == [("gaz", "b"), ("gaz", "c"), ("gaz", "a")]

    def test_handles_different_gazetteer_names(self):
        """Test that resolver handles referents from different gazetteers."""
        # Arrange
        texts = ["Paris and Zurich"]
        references = [[(0, 5), (10, 16)]]
        referents = [[("geonames", "2988507"), ("swissnames3d", "12345")]]
        resolver = ManualResolver(
            label="test", texts=texts, references=references, referents=referents
        )

        # Act
        results = resolver.predict(texts, references)

        # Assert
        assert len(results[0]) == 2
        assert results[0][0][0] == "geonames"
        assert results[0][1][0] == "swissnames3d"

    def test_handles_large_reference_set(self):
        """Test that ManualResolver can handle many references efficiently."""
        # Arrange
        num_refs = 50
        text = " ".join([f"City{i}" for i in range(num_refs)])
        references = []
        referents = []
        position = 0
        for i in range(num_refs):
            city_name = f"City{i}"
            references.append((position, position + len(city_name)))
            referents.append(("geonames", str(1000 + i)))
            position += len(city_name) + 1  # +1 for space

        texts = [text]
        references_list = [references]
        referents_list = [referents]

        resolver = ManualResolver(
            label="test",
            texts=texts,
            references=references_list,
            referents=referents_list,
        )

        # Act
        results = resolver.predict(texts, references_list)

        # Assert
        assert len(results) == 1
        assert len(results[0]) == num_refs
        assert all(ref is not None for ref in results[0])

    def test_config_contains_only_label(self):
        """Test that resolver config contains only the label."""
        # Arrange
        texts = ["Paris"]
        references = [[(0, 5)]]
        referents = [[("geonames", "2988507")]]

        # Act
        resolver = ManualResolver(
            label="my_label",
            texts=texts,
            references=references,
            referents=referents,
        )

        # Assert
        assert resolver.config == {"label": "my_label"}
        assert "texts" not in resolver.config
        assert "references" not in resolver.config
        assert "referents" not in resolver.config

    def test_handles_documents_with_varying_reference_counts(self):
        """Test that resolver handles documents with different numbers of references."""
        # Arrange
        texts = ["Paris", "London and Berlin", "No refs", "Tokyo"]
        references = [[(0, 5)], [(0, 6), (11, 17)], [], [(0, 5)]]
        referents = [
            [("geonames", "2988507")],
            [("geonames", "2643743"), ("geonames", "2950159")],
            [],
            [("geonames", "1850144")],
        ]
        resolver = ManualResolver(
            label="test", texts=texts, references=references, referents=referents
        )

        # Act
        results = resolver.predict(texts, references)

        # Assert
        assert len(results) == 4
        assert len(results[0]) == 1
        assert len(results[1]) == 2
        assert len(results[2]) == 0
        assert len(results[3]) == 1
