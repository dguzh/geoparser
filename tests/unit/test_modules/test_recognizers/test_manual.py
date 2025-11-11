"""
Unit tests for geoparser/modules/recognizers/manual.py

Tests the ManualRecognizer module for handling manually annotated references.
"""

import pytest

from geoparser.modules.recognizers.manual import ManualRecognizer


@pytest.mark.unit
class TestManualRecognizerInitialization:
    """Test ManualRecognizer initialization."""

    def test_creates_with_required_parameters(self):
        """Test that ManualRecognizer can be created with required parameters."""
        # Arrange & Act
        recognizer = ManualRecognizer(
            label="test", texts=["Text 1"], references=[[(0, 4)]]
        )

        # Assert
        assert recognizer.label == "test"
        assert recognizer.texts == ["Text 1"]
        assert recognizer.references == [[(0, 4)]]

    def test_sets_name_from_class_attribute(self):
        """Test that NAME is set correctly."""
        # Arrange & Act
        recognizer = ManualRecognizer(label="test", texts=[], references=[])

        # Assert
        assert recognizer.name == "ManualRecognizer"

    def test_config_contains_only_label(self):
        """Test that config only contains the label (not texts or references)."""
        # Arrange & Act
        recognizer = ManualRecognizer(
            label="my_label", texts=["Text"], references=[[(0, 1)]]
        )

        # Assert
        assert recognizer.config == {"label": "my_label"}
        assert "texts" not in recognizer.config
        assert "references" not in recognizer.config

    def test_different_labels_produce_different_ids(self):
        """Test that different labels produce different module IDs."""
        # Arrange
        recognizer1 = ManualRecognizer(label="label1", texts=[], references=[])
        recognizer2 = ManualRecognizer(label="label2", texts=[], references=[])

        # Act & Assert
        assert recognizer1.id != recognizer2.id

    def test_same_label_produces_same_id(self):
        """Test that same label produces same module ID regardless of data."""
        # Arrange
        recognizer1 = ManualRecognizer(
            label="same", texts=["Text 1"], references=[[(0, 1)]]
        )
        recognizer2 = ManualRecognizer(
            label="same", texts=["Different text"], references=[[(5, 10)]]
        )

        # Act & Assert
        assert recognizer1.id == recognizer2.id


@pytest.mark.unit
class TestManualRecognizerPredict:
    """Test ManualRecognizer predict method."""

    def test_returns_references_for_matching_text(self):
        """Test that predict returns references for texts that match stored texts."""
        # Arrange
        recognizer = ManualRecognizer(
            label="test",
            texts=["New York is a city."],
            references=[[(0, 8)]],  # "New York"
        )

        # Act
        results = recognizer.predict(["New York is a city."])

        # Assert
        assert len(results) == 1
        assert results[0] == [(0, 8)]

    def test_returns_none_for_non_matching_text(self):
        """Test that predict returns None for texts not in stored annotations."""
        # Arrange
        recognizer = ManualRecognizer(
            label="test", texts=["Text 1"], references=[[(0, 4)]]
        )

        # Act
        results = recognizer.predict(["Different text"])

        # Assert
        assert len(results) == 1
        assert results[0] is None

    def test_handles_multiple_texts(self):
        """Test that predict handles multiple input texts correctly."""
        # Arrange
        recognizer = ManualRecognizer(
            label="test",
            texts=["Text 1", "Text 2"],
            references=[[(0, 4)], [(0, 4)]],
        )

        # Act
        results = recognizer.predict(["Text 1", "Text 2", "Text 3"])

        # Assert
        assert len(results) == 3
        assert results[0] == [(0, 4)]
        assert results[1] == [(0, 4)]
        assert results[2] is None

    def test_returns_multiple_references_for_single_text(self):
        """Test that predict returns multiple references for a single text."""
        # Arrange
        recognizer = ManualRecognizer(
            label="test",
            texts=["Paris and London are cities."],
            references=[[(0, 5), (10, 16)]],  # "Paris" and "London"
        )

        # Act
        results = recognizer.predict(["Paris and London are cities."])

        # Assert
        assert len(results) == 1
        assert len(results[0]) == 2
        assert results[0] == [(0, 5), (10, 16)]

    def test_returns_empty_list_for_annotated_text_with_no_references(self):
        """Test that predict returns empty list for text annotated as having no references."""
        # Arrange
        recognizer = ManualRecognizer(
            label="test",
            texts=["No toponyms here."],
            references=[[]],  # Explicitly annotated as having no references
        )

        # Act
        results = recognizer.predict(["No toponyms here."])

        # Assert
        assert len(results) == 1
        assert results[0] == []

    def test_distinguishes_empty_list_from_none(self):
        """Test that predict distinguishes between [] (annotated) and None (not annotated)."""
        # Arrange
        recognizer = ManualRecognizer(
            label="test",
            texts=["Annotated text"],
            references=[[]],  # Annotated as empty
        )

        # Act
        results = recognizer.predict(["Annotated text", "Unannotated text"])

        # Assert
        assert results[0] == []  # Explicitly annotated as empty
        assert results[1] is None  # Not annotated

    def test_exact_text_matching(self):
        """Test that predict uses exact text matching."""
        # Arrange
        recognizer = ManualRecognizer(
            label="test", texts=["Paris"], references=[[(0, 5)]]
        )

        # Act
        results = recognizer.predict(["Paris", "Paris ", " Paris", "paris"])

        # Assert
        assert results[0] == [(0, 5)]  # Exact match
        assert results[1] is None  # Different (extra space)
        assert results[2] is None  # Different (leading space)
        assert results[3] is None  # Different (case)

    def test_preserves_reference_order(self):
        """Test that predict preserves the order of references."""
        # Arrange
        recognizer = ManualRecognizer(
            label="test",
            texts=["Text"],
            references=[[(10, 15), (5, 8), (0, 3)]],  # Not in order
        )

        # Act
        results = recognizer.predict(["Text"])

        # Assert
        assert results[0] == [(10, 15), (5, 8), (0, 3)]  # Order preserved
