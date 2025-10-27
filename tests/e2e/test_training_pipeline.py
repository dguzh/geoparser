"""
End-to-end tests for training pipeline.

Tests the complete training workflow including data preparation, model training,
and integration with Project API.

Note: These tests use Project API for proper context management instead of manually
calling _set_recognizer_context or _set_resolver_context.
"""

import pytest

from geoparser.modules.recognizers.manual import ManualRecognizer
from geoparser.modules.resolvers.manual import ManualResolver
from geoparser.project import Project
from geoparser.services.recognition import RecognitionService
from geoparser.services.resolution import ResolutionService


@pytest.mark.e2e
class TestRecognizerTraining:
    """End-to-end tests for recognizer training workflows."""

    def test_train_recognizer_via_recognition_service(
        self, test_session, real_spacy_recognizer, tmp_path
    ):
        """Test that RecognitionService.fit trains a recognizer using annotated documents."""
        # Arrange - Create project with annotations
        project = Project("recognizer_service_training")
        texts = ["Paris is beautiful.", "London is historic.", "Berlin is vibrant."]
        references = [[(0, 5)], [(0, 6)], [(0, 6)]]  # Paris, London, Berlin

        project.create_documents(texts)
        project.create_references(
            label="training_annotations", texts=texts, references=references
        )

        # Get annotation ID
        from geoparser.db.crud import RecognizerRepository

        recognizers = RecognizerRepository.get_all(test_session)
        annotator_id = recognizers[0].id

        # Get documents with context set via Project API
        documents = project.get_documents(recognizer_id=annotator_id)

        # Create service with trainable recognizer
        service = RecognitionService(real_spacy_recognizer)
        output_path = tmp_path / "trained_recognizer"

        # Act - Train the recognizer
        service.fit(documents, output_path=str(output_path), epochs=1)

        # Assert - Model should be saved
        assert output_path.exists()
        # Check that model files were created
        assert len(list(output_path.iterdir())) > 0

        # Cleanup
        project.delete()

    def test_train_recognizer_via_project_api(
        self, test_session, real_spacy_recognizer, tmp_path
    ):
        """Test that Project.train_recognizer trains using annotated documents."""
        # Arrange
        project = Project("recognizer_training_test")
        texts = ["Sydney is in Australia.", "Tokyo is in Japan."]
        references = [[(0, 6)], [(0, 5)]]  # Sydney, Tokyo

        project.create_documents(texts)
        project.create_references(
            label="training_data", texts=texts, references=references
        )

        # Get the recognizer ID that was created
        from geoparser.db.crud import RecognizerRepository

        recognizers = RecognizerRepository.get_all(test_session)
        recognizer_id = recognizers[0].id

        output_path = tmp_path / "project_trained_recognizer"

        # Act
        project.train_recognizer(
            recognizer=real_spacy_recognizer,
            recognizer_id=recognizer_id,
            output_path=str(output_path),
            epochs=1,
        )

        # Assert
        assert output_path.exists()
        # Verify model files were created
        model_files = list(output_path.iterdir())
        assert len(model_files) > 0

        # Cleanup
        project.delete()

    def test_train_recognizer_with_custom_parameters(
        self, test_session, real_spacy_recognizer, tmp_path
    ):
        """Test that custom training parameters are passed through correctly."""
        # Arrange
        project = Project("custom_params_training")
        texts = ["Madrid is in Spain."]
        references = [[(0, 6)]]  # Madrid

        project.create_documents(texts)
        project.create_references(
            label="custom_params", texts=texts, references=references
        )

        from geoparser.db.crud import RecognizerRepository

        recognizers = RecognizerRepository.get_all(test_session)
        annotator_id = recognizers[0].id

        documents = project.get_documents(recognizer_id=annotator_id)

        service = RecognitionService(real_spacy_recognizer)
        output_path = tmp_path / "custom_params_model"

        # Act - Use custom training parameters
        service.fit(
            documents,
            output_path=str(output_path),
            epochs=2,
            batch_size=4,
            dropout=0.2,
            learning_rate=0.002,
        )

        # Assert
        assert output_path.exists()

        # Cleanup
        project.delete()

    def test_train_recognizer_raises_error_without_annotations(
        self, real_spacy_recognizer, tmp_path
    ):
        """Test that training raises error when documents have no reference annotations."""
        # Arrange - Create project with documents but no annotations
        project = Project("no_annotations")
        texts = ["No annotations here.", "Also no annotations."]

        project.create_documents(texts)
        documents = project.get_documents()

        service = RecognitionService(real_spacy_recognizer)
        output_path = tmp_path / "no_annotations_model"

        # Act & Assert
        with pytest.raises(ValueError, match="No training examples found"):
            service.fit(documents, output_path=str(output_path), epochs=1)

        # Cleanup
        project.delete()

    def test_train_recognizer_raises_error_for_non_trainable_module(
        self, test_session, tmp_path
    ):
        """Test that training raises error for recognizers without fit method."""
        # Arrange
        project = Project("non_trainable_test")
        texts = ["Test text."]
        references = [[(0, 4)]]  # "Test"

        project.create_documents(texts)
        project.create_references(
            label="annotations", texts=texts, references=references
        )

        from geoparser.db.crud import RecognizerRepository

        recognizers = RecognizerRepository.get_all(test_session)
        annotator_id = recognizers[0].id

        documents = project.get_documents(recognizer_id=annotator_id)

        # ManualRecognizer doesn't have fit method
        non_trainable = ManualRecognizer(
            label="non_trainable", texts=texts, references=references
        )
        service = RecognitionService(non_trainable)

        # Act & Assert
        with pytest.raises(ValueError, match="does not implement a fit method"):
            service.fit(documents, output_path=str(tmp_path / "model"))

        # Cleanup
        project.delete()

    def test_train_recognizer_extracts_references_from_document_toponyms(
        self, test_session, real_spacy_recognizer, tmp_path
    ):
        """Test that fit correctly extracts references from document.toponyms property."""
        # Arrange
        project = Project("toponyms_extraction")
        texts = ["Rome is in Italy.", "Athens is in Greece."]
        references = [[(0, 4)], [(0, 6)]]  # Rome, Athens

        project.create_documents(texts)
        project.create_references(
            label="toponyms_test", texts=texts, references=references
        )

        from geoparser.db.crud import RecognizerRepository

        recognizers = RecognizerRepository.get_all(test_session)
        annotator_id = recognizers[0].id

        documents = project.get_documents(recognizer_id=annotator_id)

        # Verify toponyms are set correctly
        assert len(documents[0].toponyms) == 1
        assert len(documents[1].toponyms) == 1

        service = RecognitionService(real_spacy_recognizer)
        output_path = tmp_path / "toponyms_extraction_model"

        # Act - Should successfully extract references from toponyms
        service.fit(documents, output_path=str(output_path), epochs=1)

        # Assert
        assert output_path.exists()

        # Cleanup
        project.delete()

    def test_train_recognizer_handles_multiple_references_per_document(
        self, test_session, real_spacy_recognizer, tmp_path
    ):
        """Test that training handles documents with multiple references correctly."""
        # Arrange
        project = Project("multi_ref")
        texts = ["Travel from Paris to London and then to Berlin."]
        references = [[(12, 17), (21, 27), (41, 47)]]  # Paris, London, Berlin

        project.create_documents(texts)
        project.create_references(label="multi_ref", texts=texts, references=references)

        from geoparser.db.crud import RecognizerRepository

        recognizers = RecognizerRepository.get_all(test_session)
        annotator_id = recognizers[0].id

        documents = project.get_documents(recognizer_id=annotator_id)

        # Verify multiple toponyms
        assert len(documents[0].toponyms) == 3

        service = RecognitionService(real_spacy_recognizer)
        output_path = tmp_path / "multi_ref_model"

        # Act
        service.fit(documents, output_path=str(output_path), epochs=1)

        # Assert
        assert output_path.exists()

        # Cleanup
        project.delete()


@pytest.mark.e2e
class TestResolverTraining:
    """End-to-end tests for resolver training workflows."""

    def test_train_resolver_via_resolution_service(
        self,
        test_session,
        real_sentencetransformer_resolver,
        andorra_gazetteer,
        tmp_path,
    ):
        """Test that ResolutionService.fit trains a resolver using annotated documents."""
        # Arrange - Create project with annotations
        project = Project("resolver_service_training")
        texts = [
            "Andorra la Vella is the capital.",
            "Visit les Escaldes.",
            "Encamp is a parish.",
        ]
        references = [[(0, 17)], [(6, 18)], [(0, 6)]]
        referents = [
            [("andorranames", "3041563")],  # Andorra la Vella
            [("andorranames", "3040051")],  # les Escaldes
            [("andorranames", "3041204")],  # Encamp
        ]

        project.create_documents(texts)
        project.create_references(
            label="ref_annotations", texts=texts, references=references
        )
        project.create_referents(
            label="res_annotations",
            texts=texts,
            references=references,
            referents=referents,
        )

        # Get annotation IDs
        from geoparser.db.crud import RecognizerRepository, ResolverRepository

        recognizers = RecognizerRepository.get_all(test_session)
        ref_annotator_id = recognizers[0].id
        resolvers = ResolverRepository.get_all(test_session)
        res_annotator_id = resolvers[0].id

        # Get documents with contexts set via Project API
        documents = project.get_documents(
            recognizer_id=ref_annotator_id, resolver_id=res_annotator_id
        )

        # Create service with trainable resolver
        service = ResolutionService(real_sentencetransformer_resolver)
        output_path = tmp_path / "trained_resolver"

        # Act - Train the resolver
        service.fit(documents, output_path=str(output_path), epochs=1)

        # Assert - Model should be saved
        assert output_path.exists()
        # Check that model files were created
        assert len(list(output_path.iterdir())) > 0

        # Cleanup
        project.delete()

    def test_train_resolver_via_project_api(
        self,
        test_session,
        real_sentencetransformer_resolver,
        andorra_gazetteer,
        tmp_path,
    ):
        """Test that Project.train_resolver trains using annotated documents."""
        # Arrange
        project = Project("resolver_training_test")
        texts = ["Ordino is beautiful.", "La Massana is scenic."]
        references = [[(0, 6)], [(0, 10)]]
        referents = [
            [("andorranames", "3039163")],  # Ordino
            [("andorranames", "3039678")],  # La Massana
        ]

        project.create_documents(texts)
        project.create_references(
            label="training_data", texts=texts, references=references
        )
        project.create_referents(
            label="training_data",
            texts=texts,
            references=references,
            referents=referents,
        )

        # Get the recognizer and resolver IDs
        from geoparser.db.crud import RecognizerRepository, ResolverRepository

        recognizers = RecognizerRepository.get_all(test_session)
        recognizer_id = recognizers[0].id
        resolvers = ResolverRepository.get_all(test_session)
        resolver_id = resolvers[0].id

        output_path = tmp_path / "project_trained_resolver"

        # Act
        project.train_resolver(
            resolver=real_sentencetransformer_resolver,
            recognizer_id=recognizer_id,
            resolver_id=resolver_id,
            output_path=str(output_path),
            epochs=1,
        )

        # Assert
        assert output_path.exists()
        # Verify model files were created
        model_files = list(output_path.iterdir())
        assert len(model_files) > 0

        # Cleanup
        project.delete()

    def test_train_resolver_with_custom_parameters(
        self,
        test_session,
        real_sentencetransformer_resolver,
        andorra_gazetteer,
        tmp_path,
    ):
        """Test that custom training parameters are passed through correctly."""
        # Arrange
        project = Project("custom_params_resolver")
        texts = ["Canillo is a parish."]
        references = [[(0, 7)]]  # Canillo
        referents = [[("andorranames", "3041581")]]

        project.create_documents(texts)
        project.create_references(
            label="custom_ref", texts=texts, references=references
        )
        project.create_referents(
            label="custom_res",
            texts=texts,
            references=references,
            referents=referents,
        )

        from geoparser.db.crud import RecognizerRepository, ResolverRepository

        recognizers = RecognizerRepository.get_all(test_session)
        ref_annotator_id = recognizers[0].id
        resolvers = ResolverRepository.get_all(test_session)
        res_annotator_id = resolvers[0].id

        documents = project.get_documents(
            recognizer_id=ref_annotator_id, resolver_id=res_annotator_id
        )

        service = ResolutionService(real_sentencetransformer_resolver)
        output_path = tmp_path / "custom_params_resolver"

        # Act - Use custom training parameters
        service.fit(
            documents,
            output_path=str(output_path),
            epochs=2,
            batch_size=4,
            learning_rate=1e-5,
            warmup_ratio=0.2,
        )

        # Assert
        assert output_path.exists()

        # Cleanup
        project.delete()

    def test_train_resolver_raises_error_without_referents(
        self,
        test_session,
        real_sentencetransformer_resolver,
        tmp_path,
    ):
        """Test that training raises error when documents have no referent annotations."""
        # Arrange - Create project with references but no referents
        project = Project("no_referents")
        texts = ["Test location."]
        references = [[(0, 4)]]

        project.create_documents(texts)
        project.create_references(
            label="no_referents", texts=texts, references=references
        )

        from geoparser.db.crud import RecognizerRepository

        recognizers = RecognizerRepository.get_all(test_session)
        ref_annotator_id = recognizers[0].id

        # Get documents without resolver context
        documents = project.get_documents(recognizer_id=ref_annotator_id)

        service = ResolutionService(real_sentencetransformer_resolver)
        output_path = tmp_path / "no_referents_model"

        # Act & Assert
        with pytest.raises(ValueError, match="No training examples found"):
            service.fit(documents, output_path=str(output_path), epochs=1)

        # Cleanup
        project.delete()

    def test_train_resolver_raises_error_for_non_trainable_module(
        self,
        test_session,
        andorra_gazetteer,
        tmp_path,
    ):
        """Test that training raises error for resolvers without fit method."""
        # Arrange
        project = Project("non_trainable_resolver")
        texts = ["Test text."]
        references = [[(0, 4)]]
        referents = [[("andorranames", "3041563")]]

        project.create_documents(texts)
        project.create_references(
            label="annotations", texts=texts, references=references
        )
        project.create_referents(
            label="annotations",
            texts=texts,
            references=references,
            referents=referents,
        )

        from geoparser.db.crud import RecognizerRepository, ResolverRepository

        recognizers = RecognizerRepository.get_all(test_session)
        ref_annotator_id = recognizers[0].id
        resolvers = ResolverRepository.get_all(test_session)
        res_annotator_id = resolvers[0].id

        documents = project.get_documents(
            recognizer_id=ref_annotator_id, resolver_id=res_annotator_id
        )

        # ManualResolver doesn't have fit method
        non_trainable = ManualResolver(
            label="non_trainable",
            texts=texts,
            references=references,
            referents=referents,
        )
        service = ResolutionService(non_trainable)

        # Act & Assert
        with pytest.raises(ValueError, match="does not implement a fit method"):
            service.fit(documents, output_path=str(tmp_path / "model"))

        # Cleanup
        project.delete()

    def test_train_resolver_extracts_referents_from_reference_location(
        self,
        test_session,
        real_sentencetransformer_resolver,
        andorra_gazetteer,
        tmp_path,
    ):
        """Test that fit correctly extracts referents from reference.location property."""
        # Arrange
        project = Project("location_extraction")
        texts = ["Sant Julia de Loria is south.", "Escaldes-Engordany is central."]
        references = [[(0, 20)], [(0, 18)]]
        referents = [
            [("andorranames", "3039162")],  # Sant Julia de Loria
            [("andorranames", "3040684")],  # Escaldes-Engordany
        ]

        project.create_documents(texts)
        project.create_references(
            label="location_test", texts=texts, references=references
        )
        project.create_referents(
            label="location_test",
            texts=texts,
            references=references,
            referents=referents,
        )

        from geoparser.db.crud import RecognizerRepository, ResolverRepository

        recognizers = RecognizerRepository.get_all(test_session)
        ref_annotator_id = recognizers[0].id
        resolvers = ResolverRepository.get_all(test_session)
        res_annotator_id = resolvers[0].id

        documents = project.get_documents(
            recognizer_id=ref_annotator_id, resolver_id=res_annotator_id
        )

        # Verify locations are set correctly
        assert documents[0].toponyms[0].location is not None
        assert documents[1].toponyms[0].location is not None

        service = ResolutionService(real_sentencetransformer_resolver)
        output_path = tmp_path / "location_extraction_model"

        # Act - Should successfully extract referents from locations
        service.fit(documents, output_path=str(output_path), epochs=1)

        # Assert
        assert output_path.exists()

        # Cleanup
        project.delete()


@pytest.mark.e2e
class TestEndToEndTrainingWorkflow:
    """End-to-end tests for complete training workflows."""

    def test_complete_annotation_to_inference_cycle(
        self,
        test_session,
        real_spacy_recognizer,
        real_sentencetransformer_resolver,
        andorra_gazetteer,
        tmp_path,
    ):
        """Test complete workflow: annotate → train → use trained models for inference."""
        # Arrange - Phase 1: Create training data with annotations
        project = Project("training_workflow_test")
        training_texts = [
            "Andorra la Vella is the capital.",
            "les Escaldes is nearby.",
        ]
        training_references = [[(0, 17)], [(0, 12)]]
        training_referents = [
            [("andorranames", "3041563")],  # Andorra la Vella
            [("andorranames", "3040051")],  # les Escaldes
        ]

        project.create_documents(training_texts)
        project.create_references(
            label="annotations",
            texts=training_texts,
            references=training_references,
        )
        project.create_referents(
            label="annotations",
            texts=training_texts,
            references=training_references,
            referents=training_referents,
        )

        # Get annotation IDs
        from geoparser.db.crud import RecognizerRepository, ResolverRepository

        recognizers = RecognizerRepository.get_all(test_session)
        annotation_recognizer_id = recognizers[0].id
        resolvers = ResolverRepository.get_all(test_session)
        annotation_resolver_id = resolvers[0].id

        # Act - Phase 2: Train models
        recognizer_output = tmp_path / "trained_recognizer"
        resolver_output = tmp_path / "trained_resolver"

        project.train_recognizer(
            recognizer=real_spacy_recognizer,
            recognizer_id=annotation_recognizer_id,
            output_path=str(recognizer_output),
            epochs=1,
        )

        project.train_resolver(
            resolver=real_sentencetransformer_resolver,
            recognizer_id=annotation_recognizer_id,
            resolver_id=annotation_resolver_id,
            output_path=str(resolver_output),
            epochs=1,
        )

        # Assert - Phase 3: Verify models were created
        assert recognizer_output.exists()
        assert resolver_output.exists()
        assert len(list(recognizer_output.iterdir())) > 0
        assert len(list(resolver_output.iterdir())) > 0

        # Note: We don't test loading and using the trained models here
        # because that would require reinitializing the recognizer/resolver
        # with the new model paths, which is beyond the scope of this test

        # Cleanup
        project.delete()

    def test_train_multiple_models_on_same_data(
        self,
        test_session,
        real_spacy_recognizer,
        andorra_gazetteer,
        tmp_path,
    ):
        """Test training multiple recognizer configurations on the same annotated data."""
        # Arrange
        project = Project("multi_model_training")
        texts = ["Paris is beautiful.", "London is historic."]
        references = [[(0, 5)], [(0, 6)]]

        project.create_documents(texts)
        project.create_references(
            label="shared_annotations", texts=texts, references=references
        )

        from geoparser.db.crud import RecognizerRepository

        recognizers = RecognizerRepository.get_all(test_session)
        annotation_recognizer_id = recognizers[0].id

        # Act - Train with different hyperparameters
        model1_output = tmp_path / "model1"
        model2_output = tmp_path / "model2"

        project.train_recognizer(
            recognizer=real_spacy_recognizer,
            recognizer_id=annotation_recognizer_id,
            output_path=str(model1_output),
            epochs=1,
            dropout=0.1,
        )

        project.train_recognizer(
            recognizer=real_spacy_recognizer,
            recognizer_id=annotation_recognizer_id,
            output_path=str(model2_output),
            epochs=2,
            dropout=0.2,
        )

        # Assert - Both models should be created
        assert model1_output.exists()
        assert model2_output.exists()

        # Cleanup
        project.delete()

    def test_incremental_annotation_and_training(
        self,
        test_session,
        real_spacy_recognizer,
        tmp_path,
    ):
        """Test workflow where annotations are added incrementally and training is updated."""
        # Arrange - Phase 1: Initial training data
        project = Project("incremental_training")
        initial_texts = ["Berlin is great."]
        initial_references = [[(0, 6)]]

        project.create_documents(initial_texts)
        project.create_references(
            label="batch1", texts=initial_texts, references=initial_references
        )

        from geoparser.db.crud import RecognizerRepository

        recognizers = RecognizerRepository.get_all(test_session)
        batch1_recognizer_id = recognizers[0].id

        # Act - Phase 2: Train on initial data
        model1_output = tmp_path / "initial_model"
        project.train_recognizer(
            recognizer=real_spacy_recognizer,
            recognizer_id=batch1_recognizer_id,
            output_path=str(model1_output),
            epochs=1,
        )

        # Arrange - Phase 3: Add more training data
        additional_texts = ["Tokyo is amazing."]
        additional_references = [[(0, 5)]]

        project.create_documents(additional_texts)
        project.create_references(
            label="batch2", texts=additional_texts, references=additional_references
        )

        recognizers = RecognizerRepository.get_all(test_session)
        batch2_recognizer_id = [
            r.id for r in recognizers if r.name == "ManualRecognizer"
        ][-1]

        # Act - Phase 4: Train on second batch
        model2_output = tmp_path / "updated_model"
        project.train_recognizer(
            recognizer=real_spacy_recognizer,
            recognizer_id=batch2_recognizer_id,
            output_path=str(model2_output),
            epochs=1,
        )

        # Assert - Both models should exist
        assert model1_output.exists()
        assert model2_output.exists()

        # Cleanup
        project.delete()


@pytest.mark.e2e
class TestTrainingDataPreparation:
    """Tests for training data extraction and preparation."""

    def test_extracts_references_from_document_with_recognizer_context(
        self, test_session, real_spacy_recognizer, tmp_path
    ):
        """Test that training only uses references from documents with correct recognizer context."""
        # Arrange - Create two sets of annotations via Project
        project = Project("context_filtering")
        texts = ["Paris is beautiful."]

        project.create_documents(texts)

        # First set of annotations
        references1 = [[(0, 5)]]  # Paris
        project.create_references(
            label="annotator1", texts=texts, references=references1
        )

        # Second set of annotations (different positions)
        references2 = [[(6, 8)]]  # "is"
        project.create_references(
            label="annotator2", texts=texts, references=references2
        )

        from geoparser.db.crud import RecognizerRepository

        recognizers = RecognizerRepository.get_all(test_session)
        # Get first recognizer (annotator1) - they're created in order
        annotator1_id = recognizers[0].id

        # Get documents with only annotator1 context
        documents = project.get_documents(recognizer_id=annotator1_id)

        # Verify only first annotator's references are visible
        assert len(documents[0].toponyms) == 1
        assert documents[0].toponyms[0].start == 0
        assert documents[0].toponyms[0].end == 5

        service = RecognitionService(real_spacy_recognizer)
        output_path = tmp_path / "context_filtered_model"

        # Act - Train should only use annotator1's references
        service.fit(documents, output_path=str(output_path), epochs=1)

        # Assert
        assert output_path.exists()

        # Cleanup
        project.delete()

    def test_extracts_referents_from_references_with_resolver_context(
        self,
        test_session,
        real_sentencetransformer_resolver,
        andorra_gazetteer,
        tmp_path,
    ):
        """Test that training only uses referents from references with correct resolver context."""
        # Arrange
        project = Project("resolver_context_filtering")
        texts = ["Andorra la Vella is beautiful."]
        references = [[(0, 17)]]

        project.create_documents(texts)
        project.create_references(
            label="ref_context", texts=texts, references=references
        )

        # First resolver
        referents1 = [[("andorranames", "3041563")]]  # Andorra la Vella
        project.create_referents(
            label="resolver1",
            texts=texts,
            references=references,
            referents=referents1,
        )

        # Second resolver (different feature)
        referents2 = [[("andorranames", "3041565")]]  # Different feature
        project.create_referents(
            label="resolver2",
            texts=texts,
            references=references,
            referents=referents2,
        )

        from geoparser.db.crud import RecognizerRepository, ResolverRepository

        recognizers = RecognizerRepository.get_all(test_session)
        ref_annotator_id = recognizers[0].id
        resolvers = ResolverRepository.get_all(test_session)
        # Get first resolver (resolver1) - they're created in order
        resolver1_id = resolvers[0].id

        # Get documents with only resolver1 context
        documents = project.get_documents(
            recognizer_id=ref_annotator_id, resolver_id=resolver1_id
        )

        # Verify only first resolver's referents are visible
        assert documents[0].toponyms[0].location is not None
        assert documents[0].toponyms[0].location.location_id_value == "3041563"

        service = ResolutionService(real_sentencetransformer_resolver)
        output_path = tmp_path / "resolver_context_filtered"

        # Act - Train should only use resolver1's referents
        service.fit(documents, output_path=str(output_path), epochs=1)

        # Assert
        assert output_path.exists()

        # Cleanup
        project.delete()

    def test_filters_documents_without_annotations(
        self, test_session, real_spacy_recognizer, tmp_path
    ):
        """Test that training filters out documents without annotations."""
        # Arrange - Mix of annotated and unannotated documents
        project = Project("partial_annotations")
        texts = ["Paris is nice.", "Berlin is great.", "No annotations here."]

        project.create_documents(texts)

        # Only annotate first two documents
        references = [[(0, 5)], [(0, 6)]]
        project.create_references(
            label="partial_annotations",
            texts=texts[:2],  # Only first two texts
            references=references,
        )

        from geoparser.db.crud import RecognizerRepository

        recognizers = RecognizerRepository.get_all(test_session)
        annotator_id = recognizers[0].id

        documents = project.get_documents(recognizer_id=annotator_id)

        # Verify only first two have annotations
        assert len(documents[0].toponyms) == 1
        assert len(documents[1].toponyms) == 1
        assert len(documents[2].toponyms) == 0

        training_service = RecognitionService(real_spacy_recognizer)
        output_path = tmp_path / "filtered_training"

        # Act - Should train only on doc1 and doc2
        training_service.fit(documents, output_path=str(output_path), epochs=1)

        # Assert - Training should succeed with filtered data
        assert output_path.exists()

        # Cleanup
        project.delete()

    def test_handles_documents_with_multiple_references(
        self, test_session, real_spacy_recognizer, tmp_path
    ):
        """Test that training correctly handles documents with multiple references."""
        # Arrange
        project = Project("multi_references")
        texts = ["Visit Paris, London, and Berlin."]
        references = [[(6, 11), (13, 19), (25, 31)]]  # Paris, London, Berlin

        project.create_documents(texts)
        project.create_references(
            label="multi_references", texts=texts, references=references
        )

        from geoparser.db.crud import RecognizerRepository

        recognizers = RecognizerRepository.get_all(test_session)
        annotator_id = recognizers[0].id

        documents = project.get_documents(recognizer_id=annotator_id)

        # Verify all three references are present
        assert len(documents[0].toponyms) == 3

        training_service = RecognitionService(real_spacy_recognizer)
        output_path = tmp_path / "multi_ref_training"

        # Act
        training_service.fit(documents, output_path=str(output_path), epochs=1)

        # Assert
        assert output_path.exists()

        # Cleanup
        project.delete()
