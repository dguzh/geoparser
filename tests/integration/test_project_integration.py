"""
Integration tests for geoparser/project/project.py

Tests Project API with real database.
"""

import pytest

from geoparser.modules.recognizers.manual import ManualRecognizer
from geoparser.modules.resolvers.manual import ManualResolver
from geoparser.project import Project


@pytest.mark.integration
class TestProjectIntegration:
    """Integration tests for Project API with real database."""

    def test_creates_new_project(self):
        """Test that Project creates a new project in database."""
        # Act
        project = Project("integration_test_project")

        # Assert
        assert project is not None
        assert project.name == "integration_test_project"
        assert project.id is not None

        # Cleanup
        project.delete()

    def test_loads_existing_project(self):
        """Test that Project loads an existing project from database."""
        # Arrange - Create project first
        project1 = Project("existing_project")
        project_id = project1.id

        # Act - Load same project
        project2 = Project("existing_project")

        # Assert
        assert project2.id == project_id

        # Cleanup
        project1.delete()

    def test_creates_documents_in_database(self):
        """Test that create_documents persists documents to database."""
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

    def test_run_recognizer_creates_references(self):
        """Test that run_recognizer creates reference records."""
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
        documents = project.get_documents()
        assert len(documents) == 1
        assert len(documents[0].toponyms) == 1
        assert documents[0].toponyms[0].text == "Paris"

        # Cleanup
        project.delete()

    def test_run_resolver_creates_referents(self, andorra_gazetteer):
        """Test that run_resolver creates referent records."""
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
        documents = project.get_documents()
        assert len(documents) == 1
        assert len(documents[0].toponyms) == 1
        assert documents[0].toponyms[0].location is not None

        # Cleanup
        project.delete()

    def test_get_documents_filters_by_tag(self):
        """Test that get_documents filters by tag."""
        # Arrange
        project = Project("filter_test_project")
        texts = ["Paris and London."]
        project.create_documents(texts)

        rec1 = ManualRecognizer(label="rec1", texts=texts, references=[[(0, 5)]])
        rec2 = ManualRecognizer(label="rec2", texts=texts, references=[[(10, 16)]])

        project.run_recognizer(rec1, tag="tag1")
        project.run_recognizer(rec2, tag="tag2")

        # Act
        docs_tag1 = project.get_documents(tag="tag1")
        docs_tag2 = project.get_documents(tag="tag2")

        # Assert
        assert len(docs_tag1[0].toponyms) == 1
        assert docs_tag1[0].toponyms[0].text == "Paris"

        assert len(docs_tag2[0].toponyms) == 1
        assert docs_tag2[0].toponyms[0].text == "London"

        # Cleanup
        project.delete()

    def test_get_documents_filters_by_resolver_tag(self, andorra_gazetteer):
        """Test that get_documents filters by resolver tag."""
        # Arrange
        project = Project("resolver_filter_test")
        texts = ["Paris is beautiful."]
        references = [[(0, 5)]]

        project.create_documents(texts)

        # Run recognizer with one tag
        recognizer = ManualRecognizer(label="rec", texts=texts, references=references)
        project.run_recognizer(recognizer, tag="tag1")
        project.run_recognizer(recognizer, tag="tag2")

        # Run different resolvers on each tag
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

        project.run_resolver(res1, tag="tag1")
        project.run_resolver(res2, tag="tag2")

        # Act
        docs_tag1 = project.get_documents(tag="tag1")
        docs_tag2 = project.get_documents(tag="tag2")

        # Assert
        # Both should have locations, but potentially different ones
        assert docs_tag1[0].toponyms[0].location is not None
        assert docs_tag2[0].toponyms[0].location is not None

        # Cleanup
        project.delete()

    def test_delete_removes_project_and_documents(self, test_session):
        """Test that delete removes project and associated documents."""
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

    def test_create_references_with_manual_annotations(self):
        """Test that create_references uses ManualRecognizer internally."""
        # Arrange
        project = Project("manual_ref_test")
        texts = ["Paris is beautiful."]
        references = [[(0, 5)]]
        project.create_documents(texts)

        # Act
        project.create_references(
            tag="manual_annotations", texts=texts, references=references
        )

        # Assert - Get documents with the tag to see the references
        documents = project.get_documents(tag="manual_annotations")
        assert len(documents) == 1
        assert len(documents[0].toponyms) == 1
        assert documents[0].toponyms[0].text == "Paris"
        assert documents[0].toponyms[0].start == 0
        assert documents[0].toponyms[0].end == 5

        # Cleanup
        project.delete()

    def test_create_referents_with_manual_annotations(self, andorra_gazetteer):
        """Test that create_referents uses ManualResolver internally."""
        # Arrange
        project = Project("manual_referent_test")
        texts = ["Paris is beautiful."]
        references = [[(0, 5)]]
        referents = [[("andorranames", "3041563")]]

        project.create_documents(texts)
        project.create_references(tag="annotations", texts=texts, references=references)

        # Act
        project.create_referents(
            tag="annotations",
            texts=texts,
            references=references,
            referents=referents,
        )

        # Assert - Get documents with the tag to see the referents
        documents = project.get_documents(tag="annotations")
        assert len(documents) == 1
        assert len(documents[0].toponyms) == 1
        assert documents[0].toponyms[0].text == "Paris"
        assert documents[0].toponyms[0].location is not None
        assert documents[0].toponyms[0].location.source.gazetteer.name == "andorranames"
        assert documents[0].toponyms[0].location.location_id_value == "3041563"

        # Cleanup
        project.delete()

    def test_handles_multiple_documents_workflow(self, andorra_gazetteer):
        """Test complete workflow with multiple documents."""
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

        recognizer = ManualRecognizer(label="rec", texts=texts, references=references)
        project.run_recognizer(recognizer)

        resolver = ManualResolver(
            label="res",
            texts=texts,
            references=references,
            referents=referents,
        )
        project.run_resolver(resolver)

        documents = project.get_documents()

        # Assert
        assert len(documents) == 3
        assert len(documents[0].toponyms) == 1
        assert len(documents[1].toponyms) == 1
        assert len(documents[2].toponyms) == 0

        # Cleanup
        project.delete()

    def test_project_name_is_unique_identifier(self):
        """Test that project name uniquely identifies projects."""
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

    def test_handles_empty_document_list(self):
        """Test that project handles empty document list."""
        # Arrange
        project = Project("empty_docs_test")

        # Act
        project.create_documents([])
        documents = project.get_documents()

        # Assert
        assert documents == []

        # Cleanup
        project.delete()

    def test_documents_maintain_order(self):
        """Test that documents maintain their creation order."""
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

    def test_train_recognizer_with_annotated_documents(
        self, real_spacy_recognizer, tmp_path
    ):
        """Test that train_recognizer trains a recognizer using annotated documents."""
        # Arrange
        project = Project("train_rec_test")
        texts = ["Paris is beautiful.", "London is historic."]
        references = [[(0, 5)], [(0, 6)]]

        project.create_documents(texts)
        project.create_references(tag="annotations", texts=texts, references=references)

        output_path = tmp_path / "trained_recognizer"

        # Act
        project.train_recognizer(
            recognizer=real_spacy_recognizer,
            tag="annotations",
            output_path=str(output_path),
            epochs=1,
        )

        # Assert - Model should be saved
        assert output_path.exists()

        # Cleanup
        project.delete()

    def test_train_resolver_with_annotated_documents(
        self,
        real_sentencetransformer_resolver,
        andorra_gazetteer,
        tmp_path,
    ):
        """Test that train_resolver trains a resolver using annotated documents."""
        # Arrange
        project = Project("train_res_test")
        texts = ["Andorra la Vella is the capital.", "Visit les Escaldes."]
        references = [[(0, 17)], [(6, 18)]]
        referents = [[("andorranames", "3041563")], [("andorranames", "3041565")]]

        project.create_documents(texts)
        project.create_references(tag="annotations", texts=texts, references=references)
        project.create_referents(
            tag="annotations",
            texts=texts,
            references=references,
            referents=referents,
        )

        output_path = tmp_path / "trained_resolver"

        # Act
        project.train_resolver(
            resolver=real_sentencetransformer_resolver,
            tag="annotations",
            output_path=str(output_path),
            epochs=1,
        )

        # Assert - Model should be saved
        assert output_path.exists()

        # Cleanup
        project.delete()

    def test_train_recognizer_passes_custom_parameters(
        self, real_spacy_recognizer, tmp_path
    ):
        """Test that train_recognizer passes custom training parameters."""
        # Arrange
        project = Project("train_rec_params_test")
        texts = ["Berlin is in Germany."]
        references = [[(0, 6)]]

        project.create_documents(texts)
        project.create_references(tag="annotations", texts=texts, references=references)

        output_path = tmp_path / "trained_recognizer"

        # Act - Pass custom parameters
        project.train_recognizer(
            recognizer=real_spacy_recognizer,
            tag="annotations",
            output_path=str(output_path),
            epochs=2,
            batch_size=4,
            dropout=0.2,
        )

        # Assert
        assert output_path.exists()

        # Cleanup
        project.delete()

    def test_train_resolver_passes_custom_parameters(
        self,
        real_sentencetransformer_resolver,
        andorra_gazetteer,
        tmp_path,
    ):
        """Test that train_resolver passes custom training parameters."""
        # Arrange
        project = Project("train_res_params_test")
        texts = ["Encamp is a parish."]
        references = [[(0, 6)]]
        referents = [[("andorranames", "3041204")]]

        project.create_documents(texts)
        project.create_references(tag="annotations", texts=texts, references=references)
        project.create_referents(
            tag="annotations",
            texts=texts,
            references=references,
            referents=referents,
        )

        output_path = tmp_path / "trained_resolver"

        # Act - Pass custom parameters
        project.train_resolver(
            resolver=real_sentencetransformer_resolver,
            tag="annotations",
            output_path=str(output_path),
            epochs=2,
            batch_size=4,
            learning_rate=1e-5,
        )

        # Assert
        assert output_path.exists()

        # Cleanup
        project.delete()

    def test_train_recognizer_raises_error_without_fit_method(self):
        """Test that train_recognizer raises error for recognizers without fit method."""
        # Arrange
        project = Project("train_rec_error_test")
        texts = ["Test text."]
        references = [[(0, 4)]]

        project.create_documents(texts)
        project.create_references(tag="annotations", texts=texts, references=references)

        # ManualRecognizer doesn't have fit method
        non_trainable_recognizer = ManualRecognizer(
            label="test", texts=texts, references=references
        )

        # Act & Assert
        with pytest.raises(ValueError, match="does not implement a fit method"):
            project.train_recognizer(
                recognizer=non_trainable_recognizer,
                tag="annotations",
                output_path="/tmp/model",
            )

        # Cleanup
        project.delete()

    def test_train_resolver_raises_error_without_fit_method(self, andorra_gazetteer):
        """Test that train_resolver raises error for resolvers without fit method."""
        # Arrange
        project = Project("train_res_error_test")
        texts = ["Test text."]
        references = [[(0, 4)]]
        referents = [[("andorranames", "3041563")]]

        project.create_documents(texts)
        project.create_references(tag="annotations", texts=texts, references=references)
        project.create_referents(
            tag="annotations",
            texts=texts,
            references=references,
            referents=referents,
        )

        # ManualResolver doesn't have fit method
        non_trainable_resolver = ManualResolver(
            label="test", texts=texts, references=references, referents=referents
        )

        # Act & Assert
        with pytest.raises(ValueError, match="does not implement a fit method"):
            project.train_resolver(
                resolver=non_trainable_resolver,
                tag="annotations",
                output_path="/tmp/model",
            )

        # Cleanup
        project.delete()
