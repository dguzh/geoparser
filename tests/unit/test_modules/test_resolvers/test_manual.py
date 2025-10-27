"""
Unit tests for geoparser/modules/resolvers/manual.py

Tests the ManualResolver module for handling manually annotated referents.
"""

import pytest

from geoparser.modules.resolvers.manual import ManualResolver


@pytest.mark.unit
class TestManualResolverInitialization:
    """Test ManualResolver initialization."""

    def test_creates_with_required_parameters(self):
        """Test that ManualResolver can be created with required parameters."""
        # Arrange & Act
        resolver = ManualResolver(
            label="test",
            texts=["Text 1"],
            references=[[(0, 4)]],
            referents=[[("geonames", "123")]],
        )

        # Assert
        assert resolver.label == "test"
        assert resolver.texts == ["Text 1"]
        assert resolver.references == [[(0, 4)]]
        assert resolver.referents == [[("geonames", "123")]]

    def test_sets_name_from_class_attribute(self):
        """Test that NAME is set correctly."""
        # Arrange & Act
        resolver = ManualResolver(label="test", texts=[], references=[], referents=[])

        # Assert
        assert resolver.name == "ManualResolver"

    def test_config_contains_only_label(self):
        """Test that config only contains the label (not texts, references, or referents)."""
        # Arrange & Act
        resolver = ManualResolver(
            label="my_label",
            texts=["Text"],
            references=[[(0, 4)]],
            referents=[[("geonames", "123")]],
        )

        # Assert
        assert resolver.config == {"label": "my_label"}
        assert "texts" not in resolver.config
        assert "references" not in resolver.config
        assert "referents" not in resolver.config

    def test_different_labels_produce_different_ids(self):
        """Test that different labels produce different module IDs."""
        # Arrange
        resolver1 = ManualResolver(
            label="label1", texts=[], references=[], referents=[]
        )
        resolver2 = ManualResolver(
            label="label2", texts=[], references=[], referents=[]
        )

        # Act & Assert
        assert resolver1.id != resolver2.id

    def test_same_label_produces_same_id(self):
        """Test that same label produces same module ID regardless of data."""
        # Arrange
        resolver1 = ManualResolver(
            label="same",
            texts=["Text 1"],
            references=[[(0, 4)]],
            referents=[[("geonames", "123")]],
        )
        resolver2 = ManualResolver(
            label="same",
            texts=["Different text"],
            references=[[(5, 10)]],
            referents=[[("geonames", "456")]],
        )

        # Act & Assert
        assert resolver1.id == resolver2.id


@pytest.mark.unit
class TestManualResolverPredict:
    """Test ManualResolver predict method."""

    def test_returns_referents_for_matching_text_and_reference(self):
        """Test that predict returns referents for texts and references that match stored annotations."""
        # Arrange
        resolver = ManualResolver(
            label="test",
            texts=["Paris is the capital."],
            references=[[(0, 5)]],  # "Paris"
            referents=[[("geonames", "2988507")]],
        )

        # Act
        results = resolver.predict(
            texts=["Paris is the capital."], references=[[(0, 5)]]
        )

        # Assert
        assert len(results) == 1
        assert len(results[0]) == 1
        assert results[0][0] == ("geonames", "2988507")

    def test_returns_none_for_non_matching_text(self):
        """Test that predict returns None for texts not in stored annotations."""
        # Arrange
        resolver = ManualResolver(
            label="test",
            texts=["Text 1"],
            references=[[(0, 4)]],
            referents=[[("geonames", "123")]],
        )

        # Act
        results = resolver.predict(texts=["Different text"], references=[[(0, 9)]])

        # Assert
        assert len(results) == 1
        assert results[0] == [None]  # None for all references in unmatched text

    def test_returns_none_for_non_matching_reference(self):
        """Test that predict returns None for references not in stored annotations."""
        # Arrange
        resolver = ManualResolver(
            label="test",
            texts=["Test text"],
            references=[[(0, 4)]],  # "Test"
            referents=[[("geonames", "123")]],
        )

        # Act - Same text but different reference position
        results = resolver.predict(texts=["Test text"], references=[[(5, 9)]])  # "text"

        # Assert
        assert len(results) == 1
        assert results[0] == [None]  # Reference not annotated

    def test_handles_multiple_texts(self):
        """Test that predict handles multiple input texts correctly."""
        # Arrange
        resolver = ManualResolver(
            label="test",
            texts=["Text 1", "Text 2"],
            references=[[(0, 4)], [(0, 4)]],
            referents=[[("geonames", "123")], [("geonames", "456")]],
        )

        # Act
        results = resolver.predict(
            texts=["Text 1", "Text 2", "Text 3"],
            references=[[(0, 4)], [(0, 4)], [(0, 4)]],
        )

        # Assert
        assert len(results) == 3
        assert results[0] == [("geonames", "123")]
        assert results[1] == [("geonames", "456")]
        assert results[2] == [None]  # Text 3 not annotated

    def test_handles_multiple_references_per_text(self):
        """Test that predict handles multiple references in a single text."""
        # Arrange
        resolver = ManualResolver(
            label="test",
            texts=["Paris and London"],
            references=[[(0, 5), (10, 16)]],  # "Paris" and "London"
            referents=[[("geonames", "2988507"), ("geonames", "2643743")]],
        )

        # Act
        results = resolver.predict(
            texts=["Paris and London"], references=[[(0, 5), (10, 16)]]
        )

        # Assert
        assert len(results) == 1
        assert len(results[0]) == 2
        assert results[0][0] == ("geonames", "2988507")
        assert results[0][1] == ("geonames", "2643743")

    def test_handles_mixed_annotated_and_unannotated_references(self):
        """Test that predict handles mix of annotated and unannotated references."""
        # Arrange
        resolver = ManualResolver(
            label="test",
            texts=["Paris and London"],
            references=[[(0, 5)]],  # Only "Paris" is annotated
            referents=[[("geonames", "2988507")]],
        )

        # Act - Request both Paris and London
        results = resolver.predict(
            texts=["Paris and London"], references=[[(0, 5), (10, 16)]]
        )

        # Assert
        assert len(results) == 1
        assert len(results[0]) == 2
        assert results[0][0] == ("geonames", "2988507")  # Paris is annotated
        assert results[0][1] is None  # London is not annotated

    def test_exact_text_matching(self):
        """Test that predict uses exact text matching."""
        # Arrange
        resolver = ManualResolver(
            label="test",
            texts=["Paris"],
            references=[[(0, 5)]],
            referents=[[("geonames", "2988507")]],
        )

        # Act
        results = resolver.predict(
            texts=["Paris", "Paris ", " Paris", "paris"],
            references=[[(0, 5)], [(0, 6)], [(0, 6)], [(0, 5)]],
        )

        # Assert
        assert results[0] == [("geonames", "2988507")]  # Exact match
        assert results[1] == [None]  # Different (extra space)
        assert results[2] == [None]  # Different (leading space)
        assert results[3] == [None]  # Different (case)

    def test_exact_reference_matching(self):
        """Test that predict uses exact reference position matching."""
        # Arrange
        resolver = ManualResolver(
            label="test",
            texts=["Test"],
            references=[[(0, 4)]],
            referents=[[("geonames", "123")]],
        )

        # Act - Same text but different positions
        results = resolver.predict(
            texts=["Test"], references=[[(0, 3), (0, 4), (1, 4)]]
        )

        # Assert
        assert len(results[0]) == 3
        assert results[0][0] is None  # Different position (0, 3)
        assert results[0][1] == ("geonames", "123")  # Exact match (0, 4)
        assert results[0][2] is None  # Different position (1, 4)

    def test_preserves_referent_order(self):
        """Test that predict preserves the order of referents."""
        # Arrange
        resolver = ManualResolver(
            label="test",
            texts=["Text"],
            references=[[(10, 15), (5, 8), (0, 3)]],  # Not in order
            referents=[
                [("geonames", "A"), ("geonames", "B"), ("geonames", "C")]
            ],  # Corresponding order
        )

        # Act
        results = resolver.predict(
            texts=["Text"], references=[[(10, 15), (5, 8), (0, 3)]]
        )

        # Assert
        # Order should match input references order
        assert results[0][0] == ("geonames", "A")
        assert results[0][1] == ("geonames", "B")
        assert results[0][2] == ("geonames", "C")

    def test_handles_empty_referent_list_for_document(self):
        """Test that predict handles documents with no referents."""
        # Arrange
        resolver = ManualResolver(
            label="test",
            texts=["Doc1", "Doc2"],
            references=[[(0, 4)], []],  # Doc1 has reference, Doc2 has none
            referents=[[("geonames", "123")], []],
        )

        # Act
        results = resolver.predict(texts=["Doc1", "Doc2"], references=[[(0, 4)], []])

        # Assert
        assert len(results) == 2
        assert results[0] == [("geonames", "123")]
        assert results[1] == []  # No references for Doc2

    def test_returns_none_for_all_references_when_text_not_found(self):
        """Test that predict returns None for all references when text is not in annotations."""
        # Arrange
        resolver = ManualResolver(
            label="test",
            texts=["Known text"],
            references=[[(0, 5)]],
            referents=[[("geonames", "123")]],
        )

        # Act
        results = resolver.predict(
            texts=["Unknown text"], references=[[(0, 7), (8, 12)]]
        )

        # Assert
        assert len(results) == 1
        assert len(results[0]) == 2
        assert results[0][0] is None
        assert results[0][1] is None
