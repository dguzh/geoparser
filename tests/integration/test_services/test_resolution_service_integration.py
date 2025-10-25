"""
Integration tests for geoparser/services/resolution.py

Tests ResolutionService with real database, resolvers, and Andorra gazetteer.
"""

from unittest.mock import patch

import pytest

from geoparser.services.resolution import ResolutionService


@pytest.mark.integration
class TestResolutionServiceIntegration:
    """Integration tests for ResolutionService with real database."""

    def test_processes_references_with_manual_resolver(
        self,
        test_engine,
        test_session,
        real_manual_resolver,
        document_factory,
        reference_factory,
        andorra_gazetteer,
    ):
        """Test that service processes references with ManualResolver."""
        # Arrange
        text = "Test text"
        document = document_factory(text=text)
        reference = reference_factory(start=0, end=4, document_id=document.id)
        test_session.refresh(document)  # Load references relationship
        service = ResolutionService(resolver=real_manual_resolver)

        # Act
        with patch("geoparser.db.engine.get_engine", return_value=test_engine):
            service.predict([document])

        # Assert
        # Verify resolution record was created
        from geoparser.db.crud import ResolutionRepository

        resolutions = ResolutionRepository.get_by_reference(test_session, reference.id)
        assert len(resolutions) == 1
        assert resolutions[0].resolver_id == real_manual_resolver.id

    def test_creates_referents_in_database(
        self,
        test_engine,
        test_session,
        real_manual_resolver,
        document_factory,
        reference_factory,
        andorra_gazetteer,
    ):
        """Test that service creates referent records in database."""
        # Arrange
        text = "Test text"
        document = document_factory(text=text)
        reference = reference_factory(start=0, end=4, document_id=document.id)
        test_session.refresh(document)  # Load references relationship
        service = ResolutionService(resolver=real_manual_resolver)

        # Act
        with patch("geoparser.db.engine.get_engine", return_value=test_engine):
            service.predict([document])

        # Assert
        # Verify referent was created
        from geoparser.db.crud import ReferentRepository

        referents = ReferentRepository.get_by_reference(test_session, reference.id)
        assert len(referents) == 1

    def test_skips_already_processed_references(
        self,
        test_engine,
        test_session,
        real_manual_resolver,
        document_factory,
        reference_factory,
        andorra_gazetteer,
    ):
        """Test that service doesn't reprocess already resolved references."""
        # Arrange
        text = "Test text"
        document = document_factory(text=text)
        reference = reference_factory(start=0, end=4, document_id=document.id)
        test_session.refresh(document)  # Load references relationship
        service = ResolutionService(resolver=real_manual_resolver)

        # Act - Process twice
        with patch("geoparser.db.engine.get_engine", return_value=test_engine):
            service.predict([document])

            from geoparser.db.crud import ReferentRepository

            initial_referent_count = len(
                ReferentRepository.get_by_reference(test_session, reference.id)
            )

            service.predict([document])

            final_referent_count = len(
                ReferentRepository.get_by_reference(test_session, reference.id)
            )

        # Assert - Should not create duplicate referents
        assert final_referent_count == initial_referent_count

    def test_processes_multiple_documents_with_references(
        self,
        test_engine,
        test_session,
        real_manual_resolver,
        document_factory,
        reference_factory,
        andorra_gazetteer,
    ):
        """Test that service processes multiple documents."""
        # Arrange
        text1 = "Test text"
        text2 = "Test text"
        doc1 = document_factory(text=text1)
        doc2 = document_factory(text=text2)
        ref1 = reference_factory(start=0, end=4, document_id=doc1.id)
        ref2 = reference_factory(start=0, end=4, document_id=doc2.id)
        test_session.refresh(doc1)  # Load references relationship
        test_session.refresh(doc2)
        service = ResolutionService(resolver=real_manual_resolver)

        # Act
        with patch("geoparser.db.engine.get_engine", return_value=test_engine):
            service.predict([doc1, doc2])

        # Assert
        from geoparser.db.crud import ResolutionRepository

        resolutions1 = ResolutionRepository.get_by_reference(test_session, ref1.id)
        resolutions2 = ResolutionRepository.get_by_reference(test_session, ref2.id)

        assert len(resolutions1) == 1
        assert len(resolutions2) == 1

    def test_creates_resolver_record_in_database(
        self,
        test_engine,
        test_session,
        real_manual_resolver,
        document_factory,
        reference_factory,
        andorra_gazetteer,
    ):
        """Test that service ensures resolver record exists in database."""
        # Arrange
        document = document_factory(text="Test text")
        reference_factory(start=0, end=4, document_id=document.id)
        test_session.refresh(document)  # Load references relationship
        service = ResolutionService(resolver=real_manual_resolver)

        # Act
        with patch("geoparser.db.engine.get_engine", return_value=test_engine):
            service.predict([document])

        # Assert
        from geoparser.db.crud import ResolverRepository

        resolver_record = ResolverRepository.get(test_session, real_manual_resolver.id)
        assert resolver_record is not None
        assert resolver_record.name == "ManualResolver"

    def test_handles_document_with_no_references(
        self,
        test_engine,
        real_manual_resolver,
        document_factory,
        andorra_gazetteer,
    ):
        """Test that service handles documents with no references gracefully."""
        # Arrange
        document = document_factory(text="No locations here.")
        service = ResolutionService(resolver=real_manual_resolver)

        # Act & Assert - Should not raise exception
        with patch("geoparser.db.engine.get_engine", return_value=test_engine):
            service.predict([document])

    def test_links_referents_to_resolver(
        self,
        test_engine,
        test_session,
        real_manual_resolver,
        document_factory,
        reference_factory,
        andorra_gazetteer,
    ):
        """Test that created referents are linked to the correct resolver."""
        # Arrange
        text = "Test text"
        document = document_factory(text=text)
        reference = reference_factory(start=0, end=4, document_id=document.id)
        test_session.refresh(document)  # Load references relationship
        service = ResolutionService(resolver=real_manual_resolver)

        # Act
        with patch("geoparser.db.engine.get_engine", return_value=test_engine):
            service.predict([document])

        # Assert
        from geoparser.db.crud import ReferentRepository

        referents = ReferentRepository.get_by_reference(test_session, reference.id)
        assert all(ref.resolver_id == real_manual_resolver.id for ref in referents)

    def test_handles_empty_document_list(
        self, test_engine, real_manual_resolver, andorra_gazetteer
    ):
        """Test that service handles empty document list gracefully."""
        # Arrange
        service = ResolutionService(resolver=real_manual_resolver)

        # Act & Assert - Should not raise exception
        with patch("geoparser.db.engine.get_engine", return_value=test_engine):
            service.predict([])

    def test_referent_links_to_feature(
        self,
        test_engine,
        test_session,
        real_manual_resolver,
        document_factory,
        reference_factory,
        andorra_gazetteer,
    ):
        """Test that referent is correctly linked to feature in gazetteer."""
        # Arrange
        text = "Test text"
        document = document_factory(text=text)
        reference = reference_factory(start=0, end=4, document_id=document.id)
        test_session.refresh(document)  # Load references relationship
        service = ResolutionService(resolver=real_manual_resolver)

        # Act
        with patch("geoparser.db.engine.get_engine", return_value=test_engine):
            service.predict([document])

        # Assert
        from geoparser.db.crud import ReferentRepository

        referents = ReferentRepository.get_by_reference(test_session, reference.id)
        assert len(referents) == 1
        assert referents[0].feature_id is not None

    def test_transactions_are_committed(
        self,
        test_engine,
        test_session,
        real_manual_resolver,
        document_factory,
        reference_factory,
        andorra_gazetteer,
    ):
        """Test that changes are actually committed to database."""
        # Arrange
        text = "Test text"
        document = document_factory(text=text)
        reference = reference_factory(start=0, end=4, document_id=document.id)
        test_session.refresh(document)  # Load references relationship
        service = ResolutionService(resolver=real_manual_resolver)

        # Act
        with patch("geoparser.db.engine.get_engine", return_value=test_engine):
            service.predict([document])

        # Assert - Verify using test_session
        from geoparser.db.crud import ResolutionRepository

        resolutions = ResolutionRepository.get_by_reference(test_session, reference.id)
        assert len(resolutions) >= 1

    def test_handles_multiple_references_in_document(
        self,
        test_engine,
        test_session,
        real_manual_resolver,
        document_factory,
        reference_factory,
        andorra_gazetteer,
    ):
        """Test that service handles multiple references in one document."""
        # Arrange
        text = "Test text"
        document = document_factory(text=text)
        ref1 = reference_factory(start=0, end=4, document_id=document.id)
        ref2 = reference_factory(start=5, end=9, document_id=document.id)
        test_session.refresh(document)  # Load references relationship
        service = ResolutionService(resolver=real_manual_resolver)

        # Act
        with patch("geoparser.db.engine.get_engine", return_value=test_engine):
            service.predict([document])

        # Assert
        from geoparser.db.crud import ReferentRepository

        referents1 = ReferentRepository.get_by_reference(test_session, ref1.id)
        referents2 = ReferentRepository.get_by_reference(test_session, ref2.id)

        # Only ref1 should be resolved (matches "Test" in manual resolver)
        assert len(referents1) == 1
        # ref2 doesn't match the manual resolver's annotations
        assert len(referents2) == 0

    def test_handles_references_without_annotation(
        self,
        test_engine,
        test_session,
        real_manual_resolver,
        document_factory,
        reference_factory,
        andorra_gazetteer,
    ):
        """Test that service handles references that resolver returns None for."""
        # Arrange - Create reference that won't be in manual resolver's annotations
        document = document_factory(text="Unknown city here.")
        reference = reference_factory(start=0, end=7, document_id=document.id)
        test_session.refresh(document)  # Load references relationship
        service = ResolutionService(resolver=real_manual_resolver)

        # Act
        with patch("geoparser.db.engine.get_engine", return_value=test_engine):
            service.predict([document])

        # Assert
        from geoparser.db.crud import ResolutionRepository

        # Should not create resolution record for unresolved reference
        resolutions = ResolutionRepository.get_by_reference(test_session, reference.id)
        assert len(resolutions) == 0

    def test_works_with_sentencetransformer_resolver(
        self,
        test_engine,
        test_session,
        real_sentencetransformer_resolver,
        document_factory,
        reference_factory,
        andorra_gazetteer,
    ):
        """Test that service works with SentenceTransformerResolver."""
        # Arrange
        text = "Andorra la Vella is the capital."
        document = document_factory(text=text)
        reference = reference_factory(start=0, end=17, document_id=document.id)
        test_session.refresh(document)  # Load references relationship
        service = ResolutionService(resolver=real_sentencetransformer_resolver)

        # Act
        with patch("geoparser.db.engine.get_engine", return_value=test_engine):
            service.predict([document])

        # Assert
        from geoparser.db.crud import ReferentRepository

        referents = ReferentRepository.get_by_reference(test_session, reference.id)
        # Should resolve to an Andorra location
        assert len(referents) >= 1

    def test_processes_large_batch_of_references(
        self,
        test_engine,
        test_session,
        real_manual_resolver,
        document_factory,
        reference_factory,
        andorra_gazetteer,
    ):
        """Test that service can handle large batches efficiently."""
        # Arrange
        text = "Test text"
        documents = [document_factory(text=text) for i in range(10)]
        for doc in documents:
            reference_factory(start=0, end=4, document_id=doc.id)
            test_session.refresh(doc)  # Load references relationship
        service = ResolutionService(resolver=real_manual_resolver)

        # Act
        with patch("geoparser.db.engine.get_engine", return_value=test_engine):
            service.predict(documents)

        # Assert
        from geoparser.db.crud import ResolutionRepository

        for doc in documents:
            test_session.refresh(doc)
            for ref in doc.references:
                resolutions = ResolutionRepository.get_by_reference(
                    test_session, ref.id
                )
                assert len(resolutions) == 1
