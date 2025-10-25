"""
Integration tests for geoparser/services/recognition.py

Tests RecognitionService with real database and recognizers.
"""

import pytest

from geoparser.modules.recognizers.manual import ManualRecognizer
from geoparser.services.recognition import RecognitionService


@pytest.mark.integration
class TestRecognitionServiceIntegration:
    """Integration tests for RecognitionService with real database."""

    def test_processes_document_with_real_spacy_recognizer(
        self, test_session, real_spacy_recognizer, document_factory
    ):
        """Test that service processes documents with real spaCy recognizer."""
        # Arrange
        document = document_factory(text="New York is a major city.")
        service = RecognitionService(recognizer=real_spacy_recognizer)

        # Act
        service.predict([document])

        # Assert
        # Verify recognition record was created
        from geoparser.db.crud import RecognitionRepository

        recognitions = RecognitionRepository.get_by_document(test_session, document.id)
        assert len(recognitions) == 1
        assert recognitions[0].recognizer_id == real_spacy_recognizer.id

    def test_creates_references_in_database(
        self, test_session, real_spacy_recognizer, document_factory
    ):
        """Test that service creates reference records in database."""
        # Arrange
        document = document_factory(text="Paris and London are cities.")
        service = RecognitionService(recognizer=real_spacy_recognizer)

        # Act
        service.predict([document])

        # Assert
        # Verify references were created
        from geoparser.db.crud import ReferenceRepository

        references = ReferenceRepository.get_by_document(test_session, document.id)
        assert len(references) > 0  # Should find at least some locations

    def test_skips_already_processed_documents(
        self, test_session, real_spacy_recognizer, document_factory
    ):
        """Test that service doesn't reprocess already recognized documents."""
        # Arrange
        document = document_factory(text="Berlin is in Germany.")
        service = RecognitionService(recognizer=real_spacy_recognizer)

        # Act - Process twice
        service.predict([document])

        from geoparser.db.crud import ReferenceRepository

        initial_ref_count = len(
            ReferenceRepository.get_by_document(test_session, document.id)
        )

        service.predict([document])

        final_ref_count = len(
            ReferenceRepository.get_by_document(test_session, document.id)
        )

        # Assert - Should not create duplicate references
        assert final_ref_count == initial_ref_count

    def test_processes_multiple_documents(
        self, test_session, real_spacy_recognizer, document_factory
    ):
        """Test that service processes multiple documents in one batch."""
        # Arrange
        doc1 = document_factory(text="Paris is beautiful.")
        doc2 = document_factory(text="London is historic.")
        doc3 = document_factory(text="Berlin is vibrant.")
        service = RecognitionService(recognizer=real_spacy_recognizer)

        # Act
        service.predict([doc1, doc2, doc3])

        # Assert
        from geoparser.db.crud import RecognitionRepository

        recognitions1 = RecognitionRepository.get_by_document(test_session, doc1.id)
        recognitions2 = RecognitionRepository.get_by_document(test_session, doc2.id)
        recognitions3 = RecognitionRepository.get_by_document(test_session, doc3.id)

        assert len(recognitions1) == 1
        assert len(recognitions2) == 1
        assert len(recognitions3) == 1

    def test_creates_recognizer_record_in_database(
        self, test_session, real_spacy_recognizer, document_factory
    ):
        """Test that service ensures recognizer record exists in database."""
        # Arrange
        document = document_factory(text="Test text.")
        service = RecognitionService(recognizer=real_spacy_recognizer)

        # Act
        service.predict([document])

        # Assert
        from geoparser.db.crud import RecognizerRepository

        recognizer_record = RecognizerRepository.get(
            test_session, real_spacy_recognizer.id
        )
        assert recognizer_record is not None
        assert recognizer_record.name == "SpacyRecognizer"

    def test_handles_document_with_no_locations(
        self, test_session, real_spacy_recognizer, document_factory
    ):
        """Test that service handles documents where no locations are found."""
        # Arrange
        document = document_factory(text="The number is 42 and the color is blue.")
        service = RecognitionService(recognizer=real_spacy_recognizer)

        # Act
        service.predict([document])

        # Assert
        from geoparser.db.crud import RecognitionRepository, ReferenceRepository

        # Should still create recognition record
        recognitions = RecognitionRepository.get_by_document(test_session, document.id)
        assert len(recognitions) == 1

        # But no references
        references = ReferenceRepository.get_by_document(test_session, document.id)
        assert len(references) == 0

    def test_links_references_to_recognizer(
        self, test_session, real_spacy_recognizer, document_factory
    ):
        """Test that created references are linked to the correct recognizer."""
        # Arrange
        document = document_factory(text="Tokyo is in Japan.")
        service = RecognitionService(recognizer=real_spacy_recognizer)

        # Act
        service.predict([document])

        # Assert
        from geoparser.db.crud import ReferenceRepository

        references = ReferenceRepository.get_by_document(test_session, document.id)
        assert all(ref.recognizer_id == real_spacy_recognizer.id for ref in references)

    def test_works_with_manual_recognizer(
        self, test_session, real_manual_recognizer, document_factory
    ):
        """Test that service works with ManualRecognizer."""
        # Arrange
        # The real_manual_recognizer expects specific text
        text = "Test text with toponym"
        document = document_factory(text=text)
        service = RecognitionService(recognizer=real_manual_recognizer)

        # Act
        service.predict([document])

        # Assert
        from geoparser.db.crud import ReferenceRepository

        references = ReferenceRepository.get_by_document(test_session, document.id)
        assert len(references) == 1
        assert references[0].text == "toponym"

    def test_handles_empty_document_list(self, real_spacy_recognizer):
        """Test that service handles empty document list gracefully."""
        # Arrange
        service = RecognitionService(recognizer=real_spacy_recognizer)

        # Act & Assert - Should not raise exception
        service.predict([])

    def test_stores_correct_reference_positions(
        self, test_session, real_manual_recognizer, document_factory
    ):
        """Test that reference start and end positions are stored correctly."""
        # Arrange
        text = "Test text with toponym"
        document = document_factory(text=text)
        service = RecognitionService(recognizer=real_manual_recognizer)

        # Act
        service.predict([document])

        # Assert
        from geoparser.db.crud import ReferenceRepository

        references = ReferenceRepository.get_by_document(test_session, document.id)

        # The manual recognizer is set up to recognize "toponym" at positions (15, 22)
        toponym_ref = references[0]
        assert toponym_ref.start == 15
        assert toponym_ref.end == 22
        assert toponym_ref.text == "toponym"

    def test_transactions_are_committed(
        self, test_session, real_spacy_recognizer, document_factory
    ):
        """Test that changes are actually committed to database."""
        # Arrange
        document = document_factory(text="Berlin is great.")
        service = RecognitionService(recognizer=real_spacy_recognizer)

        # Act
        service.predict([document])

        # Assert - Verify using test_session
        from geoparser.db.crud import RecognitionRepository

        recognitions = RecognitionRepository.get_by_document(test_session, document.id)
        assert len(recognitions) >= 1

    def test_handles_text_with_multiple_entity_types(
        self, test_session, real_spacy_recognizer, document_factory
    ):
        """Test that service handles texts with various entity types."""
        # Arrange
        document = document_factory(
            text="John went to Paris. Apple released a new iPhone."
        )
        service = RecognitionService(recognizer=real_spacy_recognizer)

        # Act
        service.predict([document])

        # Assert
        from geoparser.db.crud import ReferenceRepository

        references = ReferenceRepository.get_by_document(test_session, document.id)
        # Should only get GPE/LOC entities, not PERSON or ORG
        assert any(ref.text == "Paris" for ref in references)

    def test_processes_large_batch_of_documents(
        self, test_session, real_spacy_recognizer, document_factory
    ):
        """Test that service can handle large batches efficiently."""
        # Arrange
        documents = [
            document_factory(text=f"Document {i} mentions Paris.") for i in range(20)
        ]
        service = RecognitionService(recognizer=real_spacy_recognizer)

        # Act
        service.predict(documents)

        # Assert
        from geoparser.db.crud import RecognitionRepository

        for doc in documents:
            recognitions = RecognitionRepository.get_by_document(test_session, doc.id)
            assert len(recognitions) == 1

    def test_fit_trains_recognizer_with_annotated_documents(
        self,
        test_session,
        real_spacy_recognizer,
        document_factory,
        tmp_path,
    ):
        """Test that fit method trains a recognizer using annotated documents."""
        # Arrange
        # Create documents with references
        doc1 = document_factory(text="Paris is beautiful.")
        doc2 = document_factory(text="London is historic.")

        # Create a recognizer to annotate the documents
        texts = ["Paris is beautiful.", "London is historic."]
        references = [[(0, 5)], [(0, 6)]]
        annotator = ManualRecognizer(
            label="annotator", texts=texts, references=references
        )

        # Annotate documents
        annotation_service = RecognitionService(annotator)
        annotation_service.predict([doc1, doc2])

        # Create a service with trainable recognizer
        service = RecognitionService(real_spacy_recognizer)

        # Get documents with annotations
        test_session.refresh(doc1)
        test_session.refresh(doc2)
        doc1._set_recognizer_context(annotator.id)
        doc2._set_recognizer_context(annotator.id)

        output_path = tmp_path / "trained_model"

        # Act
        service.fit([doc1, doc2], output_path=str(output_path), epochs=1)

        # Assert - Model should be saved
        assert output_path.exists()

    def test_fit_raises_error_for_recognizer_without_fit_method(
        self, document_factory, real_manual_recognizer
    ):
        """Test that fit raises error when recognizer doesn't have fit method."""
        # Arrange
        document = document_factory(text="Test text.")
        service = RecognitionService(real_manual_recognizer)

        # Act & Assert
        with pytest.raises(ValueError, match="does not implement a fit method"):
            service.fit([document], output_path="/tmp/model")

    def test_fit_extracts_references_from_document_toponyms(
        self,
        test_session,
        real_spacy_recognizer,
        document_factory,
        tmp_path,
    ):
        """Test that fit correctly extracts references from document toponyms."""
        # Arrange
        # Create and annotate documents
        doc = document_factory(text="Berlin is in Germany.")
        texts = ["Berlin is in Germany."]
        references = [[(0, 6)]]  # "Berlin"
        annotator = ManualRecognizer(
            label="annotator", texts=texts, references=references
        )

        annotation_service = RecognitionService(annotator)
        annotation_service.predict([doc])

        # Create service with trainable recognizer
        service = RecognitionService(real_spacy_recognizer)

        # Set context for document
        test_session.refresh(doc)
        doc._set_recognizer_context(annotator.id)

        output_path = tmp_path / "trained_model"

        # Act - Should extract references from toponyms
        service.fit([doc], output_path=str(output_path), epochs=1)

        # Assert
        assert output_path.exists()

    def test_fit_handles_documents_without_annotations(
        self, real_spacy_recognizer, document_factory, tmp_path
    ):
        """Test that fit handles documents without reference annotations."""
        # Arrange
        # Create documents without annotations
        doc1 = document_factory(text="No annotations here.")
        doc2 = document_factory(text="Also no annotations.")

        service = RecognitionService(real_spacy_recognizer)

        output_path = tmp_path / "trained_model"

        # Act & Assert - Should handle gracefully (no training data)
        # The fit method will call recognizer.fit which will raise ValueError
        with pytest.raises(ValueError, match="No training examples found"):
            service.fit([doc1, doc2], output_path=str(output_path), epochs=1)

    def test_fit_passes_custom_parameters_to_recognizer(
        self,
        test_session,
        real_spacy_recognizer,
        document_factory,
        tmp_path,
    ):
        """Test that fit passes custom training parameters to recognizer."""
        # Arrange
        # Create and annotate document
        doc = document_factory(text="Tokyo is in Japan.")
        texts = ["Tokyo is in Japan."]
        references = [[(0, 5)]]  # "Tokyo"
        annotator = ManualRecognizer(
            label="annotator", texts=texts, references=references
        )

        annotation_service = RecognitionService(annotator)
        annotation_service.predict([doc])

        service = RecognitionService(real_spacy_recognizer)

        test_session.refresh(doc)
        doc._set_recognizer_context(annotator.id)

        output_path = tmp_path / "trained_model"

        # Act - Pass custom parameters
        service.fit(
            [doc],
            output_path=str(output_path),
            epochs=2,
            batch_size=4,
            dropout=0.2,
        )

        # Assert
        assert output_path.exists()
