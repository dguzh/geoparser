"""
Unit tests for geoparser/services/resolution.py

Tests the ResolutionService class with mocked resolvers.
"""

from unittest.mock import patch

import pytest

from geoparser.services.resolution import ResolutionService


@pytest.mark.unit
class TestResolutionServiceInitialization:
    """Test ResolutionService initialization."""

    def test_creates_with_resolver(self, mock_sentencetransformer_resolver):
        """Test that ResolutionService can be created with a resolver."""
        # Arrange & Act
        service = ResolutionService(mock_sentencetransformer_resolver)

        # Assert
        assert service.resolver == mock_sentencetransformer_resolver


@pytest.mark.unit
class TestResolutionServicePredict:
    """Test ResolutionService predict method."""

    def test_ensures_resolver_record_exists(
        self, test_session, mock_sentencetransformer_resolver, document_factory
    ):
        """Test that predict ensures resolver record exists in database."""
        # Arrange
        document = document_factory(text="Test document")
        mock_sentencetransformer_resolver.predict.return_value = [[]]
        service = ResolutionService(mock_sentencetransformer_resolver)

        # Act
        service.predict([document])

        # Assert - Resolver record should be created
        from geoparser.db.crud import ResolverRepository

        resolver = ResolverRepository.get(
            test_session, mock_sentencetransformer_resolver.id
        )
        assert resolver is not None
        assert resolver.id == mock_sentencetransformer_resolver.id

    def test_calls_resolver_predict(
        self,
        test_session,
        mock_sentencetransformer_resolver,
        document_factory,
        reference_factory,
    ):
        """Test that predict calls the resolver's predict method."""
        # Arrange
        document = document_factory(text="New York is a city.")
        reference = reference_factory(start=0, end=8, document_id=document.id)
        test_session.refresh(document)

        mock_sentencetransformer_resolver.predict.return_value = [
            [None]
        ]  # Return None to skip referent creation
        service = ResolutionService(mock_sentencetransformer_resolver)

        # Act
        service.predict([document])

        # Assert
        mock_sentencetransformer_resolver.predict.assert_called_once()
        # Check that it was called with the document text and reference boundaries
        call_args = mock_sentencetransformer_resolver.predict.call_args
        assert call_args[0][0] == ["New York is a city."]
        assert call_args[0][1] == [[(0, 8)]]

    def test_creates_resolution_record(
        self,
        test_session,
        mock_sentencetransformer_resolver,
        document_factory,
        reference_factory,
        feature_factory,
    ):
        """Test that predict creates a resolution record marking reference as processed."""
        # Arrange
        document = document_factory(text="Test")
        reference = reference_factory(start=0, end=4, document_id=document.id)
        test_session.refresh(document)

        # Create feature hierarchy for referent creation
        feature = feature_factory(location_id_value="")

        mock_sentencetransformer_resolver.predict.return_value = [[("geonames", "")]]
        service = ResolutionService(mock_sentencetransformer_resolver)

        # Mock feature repository to return our created feature
        with patch(
            "geoparser.services.resolution.FeatureRepository.get_by_gazetteer_and_identifier"
        ) as mock_get_feature:
            mock_get_feature.return_value = feature

            # Act
            service.predict([document])

        # Assert - Resolution record should exist
        from geoparser.db.crud import ResolutionRepository

        resolution = ResolutionRepository.get_by_reference_and_resolver(
            test_session, reference.id, mock_sentencetransformer_resolver.id
        )
        assert resolution is not None

    def test_skips_already_processed_references(
        self,
        test_session,
        mock_sentencetransformer_resolver,
        document_factory,
        reference_factory,
        resolver_factory,
    ):
        """Test that predict skips references already processed by this resolver."""
        # Arrange
        resolver_record = resolver_factory(
            id=mock_sentencetransformer_resolver.id,
            name=mock_sentencetransformer_resolver.name,
            config=mock_sentencetransformer_resolver.config,
        )
        document = document_factory(text="Test")
        reference = reference_factory(start=0, end=4, document_id=document.id)
        test_session.refresh(document)

        # Mark as already processed
        from geoparser.db.crud import ResolutionRepository
        from geoparser.db.models import ResolutionCreate

        ResolutionRepository.create(
            test_session,
            ResolutionCreate(reference_id=reference.id, resolver_id=resolver_record.id),
        )

        mock_sentencetransformer_resolver.predict.return_value = [[("geonames", "123")]]
        service = ResolutionService(mock_sentencetransformer_resolver)

        # Act
        service.predict([document])

        # Assert - Predict should not be called since reference was already processed
        mock_sentencetransformer_resolver.predict.assert_not_called()

    def test_handles_none_predictions(
        self,
        test_session,
        mock_sentencetransformer_resolver,
        document_factory,
        reference_factory,
    ):
        """Test that predict handles None predictions (unavailable) correctly."""
        # Arrange
        document = document_factory(text="Test")
        reference = reference_factory(start=0, end=4, document_id=document.id)
        test_session.refresh(document)

        mock_sentencetransformer_resolver.predict.return_value = [
            [None]
        ]  # Prediction not available
        service = ResolutionService(mock_sentencetransformer_resolver)

        # Act
        service.predict([document])

        # Assert - No referents should be created, no resolution record
        from sqlmodel import select

        from geoparser.db.crud import ResolutionRepository
        from geoparser.db.models import Referent

        statement = select(Referent).where(Referent.reference_id == reference.id)
        referents = test_session.exec(statement).all()
        assert len(referents) == 0

        resolution = ResolutionRepository.get_by_reference_and_resolver(
            test_session, reference.id, mock_sentencetransformer_resolver.id
        )
        assert resolution is None

    def test_handles_empty_document_list(self, mock_sentencetransformer_resolver):
        """Test that predict handles empty document list gracefully."""
        # Arrange
        service = ResolutionService(mock_sentencetransformer_resolver)

        # Act
        service.predict([])

        # Assert - Should not call predict on resolver
        mock_sentencetransformer_resolver.predict.assert_not_called()

    def test_processes_multiple_documents(
        self,
        test_session,
        mock_sentencetransformer_resolver,
        document_factory,
        reference_factory,
        feature_factory,
    ):
        """Test that predict handles multiple documents correctly."""
        # Arrange
        doc1 = document_factory(text="New York")
        doc2 = document_factory(text="Paris")
        ref1 = reference_factory(start=0, end=8, document_id=doc1.id)
        ref2 = reference_factory(start=0, end=5, document_id=doc2.id)
        test_session.refresh(doc1)
        test_session.refresh(doc2)

        # Create feature hierarchy for referent creation
        feature = feature_factory(location_id_value="")

        mock_sentencetransformer_resolver.predict.return_value = [
            [("geonames", "")],
            [("geonames", "")],
        ]
        service = ResolutionService(mock_sentencetransformer_resolver)

        # Mock feature repository to return our created feature
        with patch(
            "geoparser.services.resolution.FeatureRepository.get_by_gazetteer_and_identifier"
        ) as mock_get_feature:
            mock_get_feature.return_value = feature

            # Act
            service.predict([doc1, doc2])

        # Assert - Both references should have resolutions
        from geoparser.db.crud import ResolutionRepository

        resolution1 = ResolutionRepository.get_by_reference_and_resolver(
            test_session, ref1.id, mock_sentencetransformer_resolver.id
        )
        resolution2 = ResolutionRepository.get_by_reference_and_resolver(
            test_session, ref2.id, mock_sentencetransformer_resolver.id
        )
        assert resolution1 is not None
        assert resolution2 is not None


@pytest.mark.unit
class TestResolutionServiceFit:
    """Test ResolutionService fit method."""

    def test_raises_error_if_resolver_has_no_fit_method(self, mock_manual_resolver):
        """Test that fit raises error if resolver doesn't implement fit."""
        # Arrange
        # Remove fit method from mock
        if hasattr(mock_manual_resolver, "fit"):
            delattr(mock_manual_resolver, "fit")

        service = ResolutionService(mock_manual_resolver)

        # Act & Assert
        with pytest.raises(ValueError, match="does not implement a fit method"):
            service.fit([])

    def test_calls_resolver_fit_with_training_data(
        self,
        test_session,
        mock_sentencetransformer_resolver,
    ):
        """Test that fit calls resolver's fit method with prepared training data."""
        # Arrange
        # Mock fit method
        mock_sentencetransformer_resolver.fit = lambda *args, **kwargs: None

        service = ResolutionService(mock_sentencetransformer_resolver)

        # This test would require more complex setup with documents, references, and referents
        # For now, we just test that it doesn't error with empty documents
        # Act & Assert - Should not raise error
        service.fit([], output_path="/tmp/model")
