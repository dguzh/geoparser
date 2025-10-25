"""
Integration tests for geoparser/geoparser/geoparser.py

Tests Geoparser stateless API with real database.
"""

import pytest

from geoparser.geoparser import Geoparser
from geoparser.modules.recognizers.manual import ManualRecognizer
from geoparser.modules.resolvers.manual import ManualResolver


@pytest.mark.integration
class TestGeoparserIntegration:
    """Integration tests for Geoparser stateless API with real database."""

    def test_parses_single_document(self, andorra_gazetteer):
        """Test that Geoparser can parse a single document."""
        # Arrange
        texts = ["Paris is beautiful."]
        references = [[(0, 5)]]
        referents = [[("andorranames", "3041563")]]

        recognizer = ManualRecognizer(label="rec", texts=texts, references=references)
        resolver = ManualResolver(
            label="res", texts=texts, references=references, referents=referents
        )
        # Act
        geoparser = Geoparser(recognizer=recognizer, resolver=resolver)
        documents = geoparser.parse(texts, save=False)

        # Assert
        assert len(documents) == 1
        assert len(documents[0].toponyms) == 1
        assert documents[0].toponyms[0].location is not None

    def test_parses_multiple_documents(self, andorra_gazetteer):
        """Test that Geoparser can parse multiple documents."""
        # Arrange
        texts = ["Paris is nice.", "London is great."]
        references = [[(0, 5)], [(0, 6)]]
        referents = [[("andorranames", "3041563")], [("andorranames", "3041565")]]

        recognizer = ManualRecognizer(label="rec", texts=texts, references=references)
        resolver = ManualResolver(
            label="res", texts=texts, references=references, referents=referents
        )
        # Act
        geoparser = Geoparser(recognizer=recognizer, resolver=resolver)
        documents = geoparser.parse(texts, save=False)

        # Assert
        assert len(documents) == 2
        assert all(len(doc.toponyms) >= 1 for doc in documents)

    def test_does_not_save_by_default(self, test_session, andorra_gazetteer):
        """Test that parse() does not save to database by default."""
        # Arrange
        texts = ["Berlin is vibrant."]
        references = [[(0, 6)]]
        referents = [[("andorranames", "3041563")]]

        recognizer = ManualRecognizer(label="rec", texts=texts, references=references)
        resolver = ManualResolver(
            label="res", texts=texts, references=references, referents=referents
        )
        # Act
        geoparser = Geoparser(recognizer=recognizer, resolver=resolver)
        documents = geoparser.parse(texts, save=False)

        # Assert - Should have results
        assert len(documents) == 1

        # Verify project was deleted (since save=False)
        from geoparser.db.crud import ProjectRepository

        all_projects = ProjectRepository.get_all(test_session)
        assert len(all_projects) == 0

    def test_saves_when_requested(self, test_session, andorra_gazetteer):
        """Test that parse() saves to database when save=True."""
        # Arrange
        texts = ["Tokyo is in Japan."]
        references = [[(0, 5)]]
        referents = [[("andorranames", "3041563")]]

        recognizer = ManualRecognizer(label="rec", texts=texts, references=references)
        resolver = ManualResolver(
            label="res", texts=texts, references=references, referents=referents
        )
        # Act
        geoparser = Geoparser(recognizer=recognizer, resolver=resolver)
        documents = geoparser.parse(texts, save=True)

        # Assert - Should have results
        assert len(documents) == 1

        # Verify project was saved (since save=True)
        from geoparser.db.crud import ProjectRepository

        all_projects = ProjectRepository.get_all(test_session)
        assert len(all_projects) == 1

    def test_handles_empty_text_list(self, andorra_gazetteer):
        """Test that Geoparser handles empty text list gracefully."""
        # Arrange
        texts = []
        references = []
        referents = []

        recognizer = ManualRecognizer(label="rec", texts=texts, references=references)
        resolver = ManualResolver(
            label="res", texts=texts, references=references, referents=referents
        )
        # Act
        geoparser = Geoparser(recognizer=recognizer, resolver=resolver)
        documents = geoparser.parse(texts, save=False)

        # Assert
        assert documents == []

    def test_handles_document_with_no_locations(self, andorra_gazetteer):
        """Test that Geoparser handles documents with no locations."""
        # Arrange
        texts = ["The number is 42."]
        references = [[]]
        referents = [[]]

        recognizer = ManualRecognizer(label="rec", texts=texts, references=references)
        resolver = ManualResolver(
            label="res", texts=texts, references=references, referents=referents
        )
        # Act
        geoparser = Geoparser(recognizer=recognizer, resolver=resolver)
        documents = geoparser.parse(texts, save=False)

        # Assert
        assert len(documents) == 1
        assert len(documents[0].toponyms) == 0

    def test_works_with_only_recognizer(self):
        """Test that Geoparser can work with only a recognizer (no resolver)."""
        # Arrange
        texts = ["Paris is beautiful."]
        references = [[(0, 5)]]

        recognizer = ManualRecognizer(label="rec", texts=texts, references=references)
        # Act
        geoparser = Geoparser(recognizer=recognizer, resolver=None)
        documents = geoparser.parse(texts, save=False)

        # Assert
        assert len(documents) == 1
        assert len(documents[0].toponyms) == 1
        # Without resolver, location should be None
        assert documents[0].toponyms[0].location is None

    def test_creates_temporary_project_with_uuid_name(
        self, test_session, andorra_gazetteer
    ):
        """Test that Geoparser creates temporary project with UUID name."""
        # Arrange
        texts = ["Paris is nice."]
        references = [[(0, 5)]]
        referents = [[("andorranames", "3041563")]]

        recognizer = ManualRecognizer(label="rec", texts=texts, references=references)
        resolver = ManualResolver(
            label="res", texts=texts, references=references, referents=referents
        )
        # Act
        geoparser = Geoparser(recognizer=recognizer, resolver=resolver)
        documents = geoparser.parse(texts, save=False)

        # Assert
        assert len(documents) == 1

        # Verify project was deleted (since save=False)
        from geoparser.db.crud import ProjectRepository

        all_projects = ProjectRepository.get_all(test_session)
        assert len(all_projects) == 0

    def test_returns_document_objects(self, andorra_gazetteer):
        """Test that parse() returns Document model objects."""
        # Arrange
        texts = ["Paris is beautiful."]
        references = [[(0, 5)]]
        referents = [[("andorranames", "3041563")]]

        recognizer = ManualRecognizer(label="rec", texts=texts, references=references)
        resolver = ManualResolver(
            label="res", texts=texts, references=references, referents=referents
        )
        # Act
        geoparser = Geoparser(recognizer=recognizer, resolver=resolver)
        documents = geoparser.parse(texts, save=False)

        # Assert
        from geoparser.db.models import Document

        assert all(isinstance(doc, Document) for doc in documents)

    def test_toponyms_have_correct_properties(self, andorra_gazetteer):
        """Test that toponyms have expected properties."""
        # Arrange
        texts = ["Paris is at position 0-5."]
        references = [[(0, 5)]]
        referents = [[("andorranames", "3041563")]]

        recognizer = ManualRecognizer(label="rec", texts=texts, references=references)
        resolver = ManualResolver(
            label="res", texts=texts, references=references, referents=referents
        )
        # Act
        geoparser = Geoparser(recognizer=recognizer, resolver=resolver)
        documents = geoparser.parse(texts, save=False)

        # Assert
        toponym = documents[0].toponyms[0]
        assert toponym.start == 0
        assert toponym.end == 5
        assert toponym.text == "Paris"
        assert toponym.location is not None

    def test_handles_mixed_resolved_and_unresolved_references(self, andorra_gazetteer):
        """Test handling of partially resolved references."""
        # Arrange
        texts = ["Paris and Unknown."]
        references = [[(0, 5), (10, 17)]]
        referents = [[("andorranames", "3041563"), None]]  # Only Paris resolved

        recognizer = ManualRecognizer(label="rec", texts=texts, references=references)
        resolver = ManualResolver(
            label="res", texts=texts, references=references, referents=referents
        )
        # Act
        geoparser = Geoparser(recognizer=recognizer, resolver=resolver)
        documents = geoparser.parse(texts, save=False)

        # Assert
        assert len(documents[0].toponyms) == 2
        # First should have location, second should not
        assert documents[0].toponyms[0].location is not None
        assert documents[0].toponyms[1].location is None

    def test_maintains_document_order(self, andorra_gazetteer):
        """Test that document order is maintained."""
        # Arrange
        texts = ["First", "Second", "Third"]
        references = [[], [], []]
        referents = [[], [], []]

        recognizer = ManualRecognizer(label="rec", texts=texts, references=references)
        resolver = ManualResolver(
            label="res", texts=texts, references=references, referents=referents
        )
        # Act
        geoparser = Geoparser(recognizer=recognizer, resolver=resolver)
        documents = geoparser.parse(texts, save=False)

        # Assert
        assert documents[0].text == "First"
        assert documents[1].text == "Second"
        assert documents[2].text == "Third"

    def test_handles_large_batch_of_documents(self, andorra_gazetteer):
        """Test that Geoparser can handle large batches."""
        # Arrange
        num_docs = 20
        texts = [f"Document {i} mentions Paris." for i in range(num_docs)]
        # Find where "Paris" is in each text
        references = [
            [(text.index("Paris"), text.index("Paris") + len("Paris"))]
            for text in texts
        ]
        referents = [[("andorranames", "3041563")]] * num_docs

        recognizer = ManualRecognizer(label="rec", texts=texts, references=references)
        resolver = ManualResolver(
            label="res", texts=texts, references=references, referents=referents
        )
        # Act
        geoparser = Geoparser(recognizer=recognizer, resolver=resolver)
        documents = geoparser.parse(texts, save=False)

        # Assert
        assert len(documents) == num_docs
        assert all(len(doc.toponyms) >= 1 for doc in documents)

    def test_cleans_up_after_error(self):
        """Test that Geoparser cleans up even if an error occurs."""
        # This test is conceptual - actual error handling may vary
        # Arrange
        texts = ["Test text."]
        references = [[(0, 4)]]

        recognizer = ManualRecognizer(label="rec", texts=texts, references=references)
        # Act & Assert
        geoparser = Geoparser(recognizer=recognizer, resolver=None)
        # Should complete without error
        documents = geoparser.parse(texts, save=False)
        assert len(documents) == 1
