"""
Integration tests for geoparser/modules/recognizers/manual.py

Tests ManualRecognizer with real database interactions.
"""

import pytest

from geoparser.modules.recognizers.manual import ManualRecognizer


@pytest.mark.integration
class TestManualRecognizerIntegration:
    """Integration tests for ManualRecognizer."""

    def test_creates_deterministic_id_from_label(self):
        """Test that ManualRecognizer generates deterministic ID from label."""
        # Arrange
        texts = ["Paris is beautiful."]
        references = [[(0, 5)]]

        # Act
        recognizer1 = ManualRecognizer(
            label="test_label", texts=texts, references=references
        )
        recognizer2 = ManualRecognizer(
            label="test_label", texts=texts, references=references
        )

        # Assert
        assert recognizer1.id == recognizer2.id

    def test_different_labels_produce_different_ids(self):
        """Test that different labels produce different recognizer IDs."""
        # Arrange
        texts = ["Paris is beautiful."]
        references = [[(0, 5)]]

        # Act
        recognizer1 = ManualRecognizer(
            label="label_a", texts=texts, references=references
        )
        recognizer2 = ManualRecognizer(
            label="label_b", texts=texts, references=references
        )

        # Assert
        assert recognizer1.id != recognizer2.id

    def test_predicts_references_for_single_document(self):
        """Test that ManualRecognizer returns references for a single document."""
        # Arrange
        texts = ["New York is a major city."]
        references = [[(0, 8)]]  # "New York"
        recognizer = ManualRecognizer(label="test", texts=texts, references=references)

        # Act
        results = recognizer.predict(texts)

        # Assert
        assert len(results) == 1
        assert results[0] == [(0, 8)]

    def test_predicts_multiple_references_in_document(self):
        """Test that ManualRecognizer handles multiple references in one document."""
        # Arrange
        texts = ["Paris and London are cities."]
        references = [[(0, 5), (10, 16)]]  # "Paris" and "London"
        recognizer = ManualRecognizer(label="test", texts=texts, references=references)

        # Act
        results = recognizer.predict(texts)

        # Assert
        assert len(results) == 1
        assert len(results[0]) == 2
        assert (0, 5) in results[0]
        assert (10, 16) in results[0]

    def test_predicts_references_for_multiple_documents(self):
        """Test that ManualRecognizer handles multiple documents."""
        # Arrange
        texts = ["Berlin is in Germany.", "Tokyo is in Japan."]
        references = [[(0, 6)], [(0, 5)]]  # "Berlin", "Tokyo"
        recognizer = ManualRecognizer(label="test", texts=texts, references=references)

        # Act
        results = recognizer.predict(texts)

        # Assert
        assert len(results) == 2
        assert results[0] == [(0, 6)]
        assert results[1] == [(0, 5)]

    def test_returns_none_for_unannotated_document(self):
        """Test that ManualRecognizer returns None for documents without annotations."""
        # Arrange
        texts = ["Paris is beautiful."]
        references = [[(0, 5)]]
        recognizer = ManualRecognizer(label="test", texts=texts, references=references)

        # Act - Query with different text
        results = recognizer.predict(["London is great."])

        # Assert
        assert len(results) == 1
        assert results[0] is None

    def test_handles_empty_reference_list(self):
        """Test that ManualRecognizer handles documents with no references."""
        # Arrange
        texts = ["No locations here."]
        references = [[]]  # No references for this document
        recognizer = ManualRecognizer(label="test", texts=texts, references=references)

        # Act
        results = recognizer.predict(texts)

        # Assert
        assert len(results) == 1
        assert results[0] == []

    def test_distinguishes_empty_list_from_none(self):
        """Test that empty list and None have different meanings."""
        # Arrange
        texts = ["Annotated with no references."]
        references = [[]]
        recognizer = ManualRecognizer(label="test", texts=texts, references=references)

        # Act
        results_annotated = recognizer.predict(texts)
        results_unannotated = recognizer.predict(["Not annotated."])

        # Assert
        assert results_annotated[0] == []  # Annotated, but no references
        assert results_unannotated[0] is None  # Not annotated at all

    def test_exact_text_matching(self):
        """Test that text matching is exact."""
        # Arrange
        texts = ["Paris is beautiful."]
        references = [[(0, 5)]]
        recognizer = ManualRecognizer(label="test", texts=texts, references=references)

        # Act - Query with slightly different text
        results = recognizer.predict(["Paris is beautiful!"])  # Added exclamation

        # Assert
        assert results[0] is None  # Should not match due to punctuation difference

    def test_mixed_annotated_and_unannotated_documents(self):
        """Test that recognizer handles mix of annotated and unannotated documents."""
        # Arrange
        texts = ["Paris is in France.", "Berlin is in Germany."]
        references = [[(0, 5)], [(0, 6)]]
        recognizer = ManualRecognizer(label="test", texts=texts, references=references)

        # Act - Query with one annotated and one unannotated text
        results = recognizer.predict(["Paris is in France.", "Tokyo is in Japan."])

        # Assert
        assert len(results) == 2
        assert results[0] == [(0, 5)]  # Annotated
        assert results[1] is None  # Not annotated

    def test_preserves_reference_order(self):
        """Test that reference order is preserved."""
        # Arrange
        texts = ["A B C"]
        references = [[(2, 3), (4, 5), (0, 1)]]  # B, C, A - not in text order
        recognizer = ManualRecognizer(label="test", texts=texts, references=references)

        # Act
        results = recognizer.predict(texts)

        # Assert
        assert results[0] == [(2, 3), (4, 5), (0, 1)]  # Order preserved as given

    def test_handles_large_document_set(self):
        """Test that ManualRecognizer can handle many documents efficiently."""
        # Arrange
        num_docs = 100
        texts = [f"Document {i} contains Paris." for i in range(num_docs)]
        # Calculate the position of "Paris" in each text
        references = []
        for text in texts:
            start = text.index("Paris")
            end = start + len("Paris")
            references.append([(start, end)])

        recognizer = ManualRecognizer(label="test", texts=texts, references=references)

        # Act
        results = recognizer.predict(texts)

        # Assert
        assert len(results) == num_docs
        assert all(len(result) == 1 for result in results)

    def test_config_contains_only_label(self):
        """Test that recognizer config contains only the label."""
        # Arrange
        texts = ["Paris"]
        references = [[(0, 5)]]

        # Act
        recognizer = ManualRecognizer(
            label="my_label", texts=texts, references=references
        )

        # Assert
        assert recognizer.config == {"label": "my_label"}
        assert "texts" not in recognizer.config
        assert "references" not in recognizer.config
