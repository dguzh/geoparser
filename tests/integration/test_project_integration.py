"""
Integration tests for geoparser/project/project.py

Tests Project API with real database.
"""

from unittest.mock import patch

import pytest

from geoparser.modules.recognizers.manual import ManualRecognizer
from geoparser.modules.resolvers.manual import ManualResolver
from geoparser.project import Project


@pytest.mark.integration
class TestProjectIntegration:
    """Integration tests for Project API with real database."""

    def test_creates_new_project(self, test_engine):
        """Test that Project creates a new project in database."""
        # Patch the engine getter to return our test engine
        with patch("geoparser.db.engine.get_engine", return_value=test_engine):
            # Act
            project = Project("integration_test_project")

            # Assert
            assert project is not None
            assert project.name == "integration_test_project"
            assert project.id is not None

            # Cleanup
            project.delete()

    def test_loads_existing_project(self, test_engine):
        """Test that Project loads an existing project from database."""
        # Patch the engine getter to return our test engine
        with patch("geoparser.db.engine.get_engine", return_value=test_engine):
            # Arrange - Create project first
            project1 = Project("existing_project")
            project_id = project1.id

            # Act - Load same project
            project2 = Project("existing_project")

            # Assert
            assert project2.id == project_id

            # Cleanup
            project1.delete()

    def test_creates_documents_in_database(self, test_engine):
        """Test that create_documents persists documents to database."""
        # Patch the engine getter to return our test engine
        with patch("geoparser.db.engine.get_engine", return_value=test_engine):
            # Arrange
            project = Project("doc_test_project")
            texts = ["First document.", "Second document."]

            # Act
            project.create_documents(texts)

            # Assert
            documents = project.get_documents()
            assert len(documents) == 2
            assert documents[0].text == "First document."
            assert documents[1].text == "Second document."

            # Cleanup
            project.delete()

    def test_run_recognizer_creates_references(self, test_engine):
        """Test that run_recognizer creates reference records."""
        # Patch the engine getter to return our test engine
        with patch("geoparser.db.engine.get_engine", return_value=test_engine):
            # Arrange
            project = Project("recognizer_test_project")
            texts = ["Paris is beautiful."]
            project.create_documents(texts)

            recognizer = ManualRecognizer(
                label="test_rec", texts=texts, references=[[(0, 5)]]
            )

            # Act
            project.run_recognizer(recognizer)

            # Assert
            documents = project.get_documents(recognizer_id=recognizer.id)
            assert len(documents) == 1
            assert len(documents[0].toponyms) == 1
            assert documents[0].toponyms[0].text == "Paris"

            # Cleanup
            project.delete()

    def test_run_resolver_creates_referents(self, test_engine, andorra_gazetteer):
        """Test that run_resolver creates referent records."""
        # Patch the engine getter to return our test engine
        with patch("geoparser.db.engine.get_engine", return_value=test_engine):
            # Arrange
            project = Project("resolver_test_project")
            texts = ["Paris is beautiful."]
            references = [[(0, 5)]]
            referents = [[("andorranames", "3041563")]]  # Using Andorra data

            project.create_documents(texts)

            recognizer = ManualRecognizer(
                label="test_rec", texts=texts, references=references
            )
            project.run_recognizer(recognizer)

            resolver = ManualResolver(
                label="test_res",
                texts=texts,
                references=references,
                referents=referents,
            )

            # Act
            project.run_resolver(resolver)

            # Assert
            documents = project.get_documents(
                recognizer_id=recognizer.id, resolver_id=resolver.id
            )
            assert len(documents) == 1
            assert len(documents[0].toponyms) == 1
            assert documents[0].toponyms[0].location is not None

            # Cleanup
            project.delete()

    def test_get_documents_filters_by_recognizer(self, test_engine):
        """Test that get_documents filters by recognizer_id."""
        # Patch the engine getter to return our test engine
        with patch("geoparser.db.engine.get_engine", return_value=test_engine):
            # Arrange
            project = Project("filter_test_project")
            texts = ["Paris and London."]
            project.create_documents(texts)

            rec1 = ManualRecognizer(label="rec1", texts=texts, references=[[(0, 5)]])
            rec2 = ManualRecognizer(label="rec2", texts=texts, references=[[(10, 16)]])

            project.run_recognizer(rec1)
            project.run_recognizer(rec2)

            # Act
            docs_rec1 = project.get_documents(recognizer_id=rec1.id)
            docs_rec2 = project.get_documents(recognizer_id=rec2.id)

            # Assert
            assert len(docs_rec1[0].toponyms) == 1
            assert docs_rec1[0].toponyms[0].text == "Paris"

            assert len(docs_rec2[0].toponyms) == 1
            assert docs_rec2[0].toponyms[0].text == "London"

            # Cleanup
            project.delete()

    def test_get_documents_filters_by_resolver(self, test_engine, andorra_gazetteer):
        """Test that get_documents filters by resolver_id."""
        # Patch the engine getter to return our test engine
        with patch("geoparser.db.engine.get_engine", return_value=test_engine):
            # Arrange
            project = Project("resolver_filter_test")
            texts = ["Paris is beautiful."]
            references = [[(0, 5)]]

            project.create_documents(texts)

            recognizer = ManualRecognizer(
                label="rec", texts=texts, references=references
            )
            project.run_recognizer(recognizer)

            res1 = ManualResolver(
                label="res1",
                texts=texts,
                references=references,
                referents=[[("andorranames", "3041563")]],
            )
            res2 = ManualResolver(
                label="res2",
                texts=texts,
                references=references,
                referents=[[("andorranames", "3041565")]],
            )

            project.run_resolver(res1)
            project.run_resolver(res2)

            # Act
            docs_res1 = project.get_documents(
                recognizer_id=recognizer.id, resolver_id=res1.id
            )
            docs_res2 = project.get_documents(
                recognizer_id=recognizer.id, resolver_id=res2.id
            )

            # Assert
            # Both should have locations, but potentially different ones
            assert docs_res1[0].toponyms[0].location is not None
            assert docs_res2[0].toponyms[0].location is not None

            # Cleanup
            project.delete()

    def test_delete_removes_project_and_documents(self, test_engine, test_session):
        """Test that delete removes project and associated documents."""
        # Patch the engine getter to return our test engine
        with patch("geoparser.db.engine.get_engine", return_value=test_engine):
            # Arrange
            project = Project("delete_test_project")
            project.create_documents(["Test document."])
            project_id = project.id

            # Act
            project.delete()

            # Assert - Verify project is gone
            from geoparser.db.crud import ProjectRepository

            retrieved = ProjectRepository.get(test_session, project_id)
            assert retrieved is None

    def test_create_references_with_manual_annotations(self, test_engine, test_session):
        """Test that create_references uses ManualRecognizer internally."""
        # Patch the engine getter to return our test engine
        with patch("geoparser.db.engine.get_engine", return_value=test_engine):
            # Arrange
            project = Project("manual_ref_test")
            texts = ["Paris is beautiful."]
            references = [[(0, 5)]]
            project.create_documents(texts)

            # Act
            project.create_references(
                label="manual_annotations", texts=texts, references=references
            )

            # Assert - Get the recognizer that was created internally
            from geoparser.db.crud import RecognizerRepository

            recognizers = RecognizerRepository.get_all(test_session)
            assert len(recognizers) == 1
            recognizer_id = recognizers[0].id

            # Get documents with the recognizer_id to see the references
            documents = project.get_documents(recognizer_id=recognizer_id)
            assert len(documents) == 1
            assert len(documents[0].toponyms) == 1
            assert documents[0].toponyms[0].text == "Paris"
            assert documents[0].toponyms[0].start == 0
            assert documents[0].toponyms[0].end == 5

            # Cleanup
            project.delete()

    def test_create_referents_with_manual_annotations(
        self, test_engine, test_session, andorra_gazetteer
    ):
        """Test that create_referents uses ManualResolver internally."""
        # Patch the engine getter to return our test engine
        with patch("geoparser.db.engine.get_engine", return_value=test_engine):
            # Arrange
            project = Project("manual_referent_test")
            texts = ["Paris is beautiful."]
            references = [[(0, 5)]]
            referents = [[("andorranames", "3041563")]]

            project.create_documents(texts)
            project.create_references(
                label="annotations", texts=texts, references=references
            )

            # Act
            project.create_referents(
                label="annotations",
                texts=texts,
                references=references,
                referents=referents,
            )

            # Assert - Get the recognizer and resolver that were created internally
            from geoparser.db.crud import RecognizerRepository, ResolverRepository

            recognizers = RecognizerRepository.get_all(test_session)
            assert len(recognizers) == 1
            recognizer_id = recognizers[0].id

            resolvers = ResolverRepository.get_all(test_session)
            assert len(resolvers) == 1
            resolver_id = resolvers[0].id

            # Get documents with both IDs to see the referents
            documents = project.get_documents(
                recognizer_id=recognizer_id, resolver_id=resolver_id
            )
            assert len(documents) == 1
            assert len(documents[0].toponyms) == 1
            assert documents[0].toponyms[0].text == "Paris"
            assert documents[0].toponyms[0].location is not None
            assert (
                documents[0].toponyms[0].location.source.gazetteer.name
                == "andorranames"
            )
            assert documents[0].toponyms[0].location.location_id_value == "3041563"

            # Cleanup
            project.delete()

    def test_handles_multiple_documents_workflow(self, test_engine, andorra_gazetteer):
        """Test complete workflow with multiple documents."""
        # Patch the engine getter to return our test engine
        with patch("geoparser.db.engine.get_engine", return_value=test_engine):
            # Arrange
            project = Project("multi_doc_workflow")
            texts = ["Paris is nice.", "London is great.", "No locations."]
            references = [[(0, 5)], [(0, 6)], []]
            referents = [
                [("andorranames", "3041563")],
                [("andorranames", "3041565")],
                [],
            ]

            # Act
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
            assert len(documents[0].toponyms) == 1
            assert len(documents[1].toponyms) == 1
            assert len(documents[2].toponyms) == 0

            # Cleanup
            project.delete()

    def test_project_name_is_unique_identifier(self, test_engine):
        """Test that project name uniquely identifies projects."""
        # Patch the engine getter to return our test engine
        with patch("geoparser.db.engine.get_engine", return_value=test_engine):
            # Arrange
            project1 = Project("unique_name")
            id1 = project1.id

            # Act - Create another project with same name
            project2 = Project("unique_name")
            id2 = project2.id

            # Assert - Should load same project
            assert id1 == id2

            # Cleanup
            project1.delete()

    def test_handles_empty_document_list(self, test_engine):
        """Test that project handles empty document list."""
        # Patch the engine getter to return our test engine
        with patch("geoparser.db.engine.get_engine", return_value=test_engine):
            # Arrange
            project = Project("empty_docs_test")

            # Act
            project.create_documents([])
            documents = project.get_documents()

            # Assert
            assert documents == []

            # Cleanup
            project.delete()

    def test_documents_maintain_order(self, test_engine):
        """Test that documents maintain their creation order."""
        # Patch the engine getter to return our test engine
        with patch("geoparser.db.engine.get_engine", return_value=test_engine):
            # Arrange
            project = Project("order_test")
            texts = ["First", "Second", "Third"]

            # Act
            project.create_documents(texts)
            documents = project.get_documents()

            # Assert
            assert documents[0].text == "First"
            assert documents[1].text == "Second"
            assert documents[2].text == "Third"

            # Cleanup
            project.delete()
