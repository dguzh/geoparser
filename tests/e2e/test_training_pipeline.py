"""
End-to-end tests for training pipeline.

Tests complete end-to-end training workflows that combine multiple components.
Basic Project training API tests are covered in integration tests.
"""

import pytest

from geoparser.project import Project


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
        """Test complete workflow: annotate → train → verify models."""
        # Arrange - Phase 1: Create training data with annotations
        project = Project("training_workflow_test")
        training_texts = [
            "Andorra la Vella is the capital.",
            "les Escaldes is nearby.",
        ]
        training_references = [[(0, 16)], [(0, 12)]]
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

        # Cleanup
        project.delete()

    def test_train_multiple_models_on_same_data(
        self,
        test_session,
        real_spacy_recognizer,
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
