"""
End-to-end tests for complete geoparsing pipeline.

Tests the full workflow from document creation through recognition and resolution.
"""

from unittest.mock import patch

import pytest

from geoparser.geoparser import Geoparser
from geoparser.modules.recognizers.manual import ManualRecognizer
from geoparser.modules.resolvers.manual import ManualResolver
from geoparser.project import Project


@pytest.mark.e2e
class TestCompleteGeoparsingPipeline:
    """End-to-end tests for complete geoparsing workflow."""

    def test_project_workflow_with_manual_modules(self, test_engine, andorra_gazetteer):
        """Test complete Project API workflow with manual recognizer and resolver."""
        # Arrange
        texts = ["Andorra la Vella is the capital of Andorra."]
        references = [[(0, 17), (39, 46)]]  # "Andorra la Vella" and "Andorra"
        referents = [
            [
                ("andorranames", "3041563"),  # Andorra la Vella
                ("andorranames", "3041565"),  # Principality of Andorra
            ]
        ]

        # Patch the engine getter to return our test engine
        # Note: andorra_gazetteer fixture already installed the gazetteer
        with patch("geoparser.db.engine.get_engine", return_value=test_engine):
            # Act - Create project and documents
            project = Project("e2e_test_project")
            project.create_documents(texts)

            # Run recognizer
            recognizer = ManualRecognizer(
                label="manual_rec", texts=texts, references=references
            )
            project.run_recognizer(recognizer)

            # Run resolver
            resolver = ManualResolver(
                label="manual_res",
                texts=texts,
                references=references,
                referents=referents,
            )
            project.run_resolver(resolver)

            # Get results
            documents = project.get_documents(
                recognizer_id=recognizer.id, resolver_id=resolver.id
            )

            # Assert
            assert len(documents) == 1
            doc = documents[0]
            assert len(doc.toponyms) == 2

            # Check first toponym (Andorra la Vella)
            toponym1 = doc.toponyms[0]
            assert toponym1.start == 0
            assert toponym1.end == 17
            assert toponym1.location is not None

            # Check second toponym (Andorra)
            toponym2 = doc.toponyms[1]
            assert toponym2.start == 39
            assert toponym2.end == 46
            assert toponym2.location is not None

            # Cleanup
            project.delete()

    def test_geoparser_stateless_workflow(self, test_engine, andorra_gazetteer):
        """Test Geoparser stateless API workflow."""
        # Arrange
        texts = ["les Escaldes is a city in Andorra."]
        references = [[(0, 12), (27, 34)]]  # "les Escaldes" and "Andorra"
        referents = [
            [
                ("andorranames", "3040051"),  # les Escaldes
                ("andorranames", "3041565"),  # Principality of Andorra
            ]
        ]

        recognizer = ManualRecognizer(
            label="manual_rec", texts=texts, references=references
        )
        resolver = ManualResolver(
            label="manual_res",
            texts=texts,
            references=references,
            referents=referents,
        )

        # Patch the engine getter to return our test engine
        # Note: andorra_gazetteer fixture already installed the gazetteer
        with patch("geoparser.db.engine.get_engine", return_value=test_engine):
            # Act
            geoparser = Geoparser(recognizer=recognizer, resolver=resolver)
            documents = geoparser.parse(texts, save=False)

            # Assert
            assert len(documents) == 1
            doc = documents[0]
            assert len(doc.toponyms) == 2

            # Both toponyms should have locations
            assert all(toponym.location is not None for toponym in doc.toponyms)

    def test_multiple_documents_workflow(self, test_engine, andorra_gazetteer):
        """Test workflow with multiple documents."""
        # Arrange - Using actual Andorra locations
        texts = [
            "Andorra la Vella is the capital.",
            "les Escaldes is nearby.",
            "No locations here.",
        ]
        references = [
            [(0, 17)],  # Doc 1: "Andorra la Vella"
            [(0, 12)],  # Doc 2: "les Escaldes"
            [],  # Doc 3: no references
        ]
        referents = [
            [("andorranames", "3041563")],  # Andorra la Vella
            [("andorranames", "3040051")],  # les Escaldes
            [],
        ]

        # Patch the engine getter to return our test engine
        # Note: andorra_gazetteer fixture already installed the gazetteer
        with patch("geoparser.db.engine.get_engine", return_value=test_engine):
            # Act
            project = Project("multi_doc_test")
            project.create_documents(texts)

            recognizer = ManualRecognizer(
                label="rec", texts=texts, references=references
            )
            project.run_recognizer(recognizer)

            resolver = ManualResolver(
                label="res",
                texts=texts,
                references=references,
                referents=referents,
            )
            project.run_resolver(resolver)

            documents = project.get_documents(
                recognizer_id=recognizer.id, resolver_id=resolver.id
            )

            # Assert
            assert len(documents) == 3

            # Doc 1: 1 toponym (Andorra la Vella)
            assert len(documents[0].toponyms) == 1
            assert documents[0].toponyms[0].location is not None

            # Doc 2: 1 toponym (les Escaldes)
            assert len(documents[1].toponyms) == 1
            assert documents[1].toponyms[0].location is not None

            # Doc 3: 0 toponyms
            assert len(documents[2].toponyms) == 0

            # Cleanup
            project.delete()

    def test_context_filtering_with_multiple_recognizers(self, test_engine):
        """Test that context filtering works with multiple recognizers."""
        # Arrange
        texts = ["Paris is a city."]

        # Two different recognizers with different results
        references1 = [[(0, 5)]]  # Just "Paris"
        references2 = [[(0, 5), (11, 15)]]  # "Paris" and "city"

        # Patch the engine getter to return our test engine
        with patch("geoparser.db.engine.get_engine", return_value=test_engine):
            # Act
            project = Project("context_test")
            project.create_documents(texts)

            # Run first recognizer
            recognizer1 = ManualRecognizer(
                label="rec1", texts=texts, references=references1
            )
            project.run_recognizer(recognizer1)

            # Run second recognizer
            recognizer2 = ManualRecognizer(
                label="rec2", texts=texts, references=references2
            )
            project.run_recognizer(recognizer2)

            # Get documents with context for recognizer1
            docs1 = project.get_documents(recognizer_id=recognizer1.id)
            # Get documents with context for recognizer2
            docs2 = project.get_documents(recognizer_id=recognizer2.id)

            # Assert
            # Recognizer1 should have 1 toponym
            assert len(docs1[0].toponyms) == 1
            assert docs1[0].toponyms[0].start == 0

            # Recognizer2 should have 2 toponyms
            assert len(docs2[0].toponyms) == 2
            assert docs2[0].toponyms[0].start == 0
            assert docs2[0].toponyms[1].start == 11

            # Cleanup
            project.delete()


@pytest.mark.e2e
class TestErrorHandling:
    """Test error handling in the pipeline."""

    def test_handles_empty_text_list(self, test_engine):
        """Test that pipeline handles empty text list gracefully."""
        # Patch the engine getter to return our test engine
        with patch("geoparser.db.engine.get_engine", return_value=test_engine):
            # Act
            project = Project("empty_test")
            project.create_documents([])
            documents = project.get_documents()

            # Assert
            assert documents == []

            # Cleanup
            project.delete()

    def test_project_delete_removes_all_data(self, test_engine, test_session):
        """Test that project.delete() removes all associated data."""
        # Arrange
        texts = ["Test text"]
        references = [[(0, 4)]]

        # Patch the engine getter to return our test engine
        with patch("geoparser.db.engine.get_engine", return_value=test_engine):
            project = Project("delete_test")
            project.create_documents(texts)

            recognizer = ManualRecognizer(
                label="rec", texts=texts, references=references
            )
            project.run_recognizer(recognizer)

            # Act
            project.delete()

            # Assert - Project should no longer exist
            from geoparser.db.crud import ProjectRepository

            retrieved_project = ProjectRepository.get(test_session, project.id)
            assert retrieved_project is None
