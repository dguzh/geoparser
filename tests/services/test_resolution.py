from unittest.mock import MagicMock, patch

from geoparser.db.crud import (
    FeatureRepository,
    ReferenceRepository,
    ReferentRepository,
    ResolutionRepository,
    ResolverRepository,
)
from geoparser.services.resolution import ResolutionService


def test_resolution_service_initialization():
    """Test basic initialization of ResolutionService."""
    mock_resolver = MagicMock()
    mock_resolver.id = "test-resolver-id"
    mock_resolver.name = "test_resolver"
    mock_resolver.config = {"param1": "value1"}

    service = ResolutionService(mock_resolver)
    assert service.resolver == mock_resolver


def test_ensure_resolver_record_existing(test_db):
    """Test _ensure_resolver_record with an existing resolver."""
    mock_resolver = MagicMock()
    mock_resolver.id = "existing-resolver-id"
    mock_resolver.name = "test_resolver"
    mock_resolver.config = {"param": "value"}

    service = ResolutionService(mock_resolver)

    with patch("geoparser.services.resolution.Session") as mock_session:
        mock_session.return_value.__enter__.return_value = test_db
        mock_session.return_value.__exit__.return_value = None

        mock_db_resolver = MagicMock()
        mock_db_resolver.id = "existing-resolver-id"

        with patch.object(
            ResolverRepository,
            "get",
            return_value=mock_db_resolver,
        ):
            with patch.object(ResolverRepository, "create") as mock_create:
                result_id = service._ensure_resolver_record(mock_resolver)
                # Should not create a new record
                mock_create.assert_not_called()
                # Should return the existing ID
                assert result_id == "existing-resolver-id"


def test_ensure_resolver_record_new(test_db):
    """Test _ensure_resolver_record with a new resolver."""
    mock_resolver = MagicMock()
    mock_resolver.id = "new-resolver-id"
    mock_resolver.name = "test_resolver"
    mock_resolver.config = {"param": "value"}

    service = ResolutionService(mock_resolver)

    with patch("geoparser.services.resolution.Session") as mock_session:
        mock_session.return_value.__enter__.return_value = test_db
        mock_session.return_value.__exit__.return_value = None

        mock_created_resolver = MagicMock()
        mock_created_resolver.id = "new-resolver-id"

        with patch.object(ResolverRepository, "get", return_value=None):
            with patch.object(
                ResolverRepository, "create", return_value=mock_created_resolver
            ) as mock_create:
                result_id = service._ensure_resolver_record(mock_resolver)
                # Should create a new record
                mock_create.assert_called_once()
                # Should return the created ID
                assert result_id == "new-resolver-id"


def test_resolution_service_run_no_documents():
    """Test run with empty document list."""
    mock_resolver = MagicMock()
    mock_resolver.id = "test-resolver-id"

    service = ResolutionService(mock_resolver)
    service.run([])  # Should return early without error


def test_resolution_service_run_no_references(test_db, test_documents):
    """Test run with documents that have no references."""
    mock_resolver = MagicMock()
    mock_resolver.id = "test-resolver-id"

    service = ResolutionService(mock_resolver)

    with patch.object(service, "_ensure_resolver_record"):
        with patch("geoparser.services.resolution.Session") as mock_session:
            mock_session.return_value.__enter__.return_value = test_db
            mock_session.return_value.__exit__.return_value = None

            with patch.object(ReferenceRepository, "get_by_document", return_value=[]):
                with patch.object(mock_resolver, "predict_referents") as mock_predict:
                    service.run(test_documents)
                    mock_predict.assert_not_called()


def test_resolution_service_run_already_processed(
    test_db, test_documents, test_references
):
    """Test run with references already processed by this resolver."""
    mock_resolver = MagicMock()
    mock_resolver.id = "test-resolver-id"

    service = ResolutionService(mock_resolver)

    with patch.object(service, "_ensure_resolver_record"):
        with patch("geoparser.services.resolution.Session") as mock_session:
            mock_session.return_value.__enter__.return_value = test_db
            mock_session.return_value.__exit__.return_value = None

            with patch.object(
                ReferenceRepository, "get_by_document", return_value=test_references
            ):
                with patch.object(
                    service, "_filter_unprocessed_references", return_value=[]
                ):
                    with patch.object(
                        mock_resolver, "predict_referents"
                    ) as mock_predict:
                        service.run(test_documents)
                        mock_predict.assert_not_called()


def test_resolution_service_run_success(test_db, test_documents, test_references):
    """Test successful run with unprocessed references."""
    mock_resolver = MagicMock()
    mock_resolver.id = "test-resolver-id"
    mock_resolver.predict_referents.return_value = [
        [("test_gazetteer", "loc1") for _ in doc_refs]
        for doc_refs in [test_references[:2], test_references[2:3]]
    ]

    service = ResolutionService(mock_resolver)

    with patch.object(
        service, "_ensure_resolver_record", return_value="test-resolver-id"
    ):
        with patch("geoparser.services.resolution.Session") as mock_session:
            mock_session.return_value.__enter__.return_value = test_db
            mock_session.return_value.__exit__.return_value = None

            # Mock get_by_document to return references per document
            # test_references has 3 refs: first 2 are doc1, last 1 is doc2
            def mock_get_by_doc(db, doc_id):
                if doc_id == test_documents[0].id:
                    return test_references[:2]
                elif doc_id == test_documents[1].id:
                    return test_references[2:3]
                return []

            with patch.object(
                ReferenceRepository, "get_by_document", side_effect=mock_get_by_doc
            ):
                with patch.object(
                    service,
                    "_filter_unprocessed_references",
                    side_effect=lambda db, refs, res_id: refs,  # Return all refs as unprocessed
                ):
                    with patch.object(
                        service, "_record_referent_predictions"
                    ) as mock_record:
                        service.run(test_documents)
                        # Should be called once per document with unprocessed references
                        assert mock_record.call_count == 2
                        # First call for doc1 with 2 references
                        mock_record.assert_any_call(
                            test_db,
                            test_references[:2],
                            [("test_gazetteer", "loc1"), ("test_gazetteer", "loc1")],
                            "test-resolver-id",
                        )
                        # Second call for doc2 with 1 reference
                        mock_record.assert_any_call(
                            test_db,
                            test_references[2:3],
                            [("test_gazetteer", "loc1")],
                            "test-resolver-id",
                        )


def test_record_referent_predictions(test_db, test_references):
    """Test _record_referent_predictions processing."""
    mock_resolver = MagicMock()
    mock_resolver.id = "test-resolver-id"

    service = ResolutionService(mock_resolver)

    predicted_referents = [("test_gazetteer", "loc1") for _ in test_references]
    resolver_id = "test-resolver-id"

    with patch.object(service, "_create_referent_record") as mock_create_ref:
        with patch.object(service, "_create_resolution_record") as mock_create_res:
            service._record_referent_predictions(
                test_db, test_references, predicted_referents, resolver_id
            )

            # Should create referent for each reference
            for ref in test_references:
                mock_create_ref.assert_any_call(
                    test_db, ref.id, "test_gazetteer", "loc1", resolver_id
                )
                mock_create_res.assert_any_call(test_db, ref.id, resolver_id)


def test_create_referent_record(test_db, test_reference):
    """Test _create_referent_record creates referent with resolver ID."""
    mock_resolver = MagicMock()
    mock_resolver.id = "test-resolver-id"

    service = ResolutionService(mock_resolver)
    resolver_id = "test-resolver-id"

    # Mock feature lookup
    mock_feature = MagicMock()
    mock_feature.id = 12345

    with patch.object(
        FeatureRepository,
        "get_by_gazetteer_and_identifier",
        return_value=mock_feature,
    ):
        with patch.object(ReferentRepository, "create") as mock_create:
            service._create_referent_record(
                test_db,
                test_reference.id,
                "test_gazetteer",
                "loc1",
                resolver_id,
            )

            mock_create.assert_called_once()
            created_args = mock_create.call_args[0][1]  # Get ReferentCreate object
            assert created_args.reference_id == test_reference.id
            assert created_args.feature_id == 12345
            assert created_args.resolver_id == resolver_id


def test_create_resolution_record(test_db, test_reference):
    """Test _create_resolution_record creates resolution record."""
    mock_resolver = MagicMock()
    mock_resolver.id = "test-resolver-id"

    service = ResolutionService(mock_resolver)
    resolver_id = "test-resolver-id"

    with patch.object(ResolutionRepository, "create") as mock_create:
        service._create_resolution_record(test_db, test_reference.id, resolver_id)

        mock_create.assert_called_once()
        created_args = mock_create.call_args[0][1]  # Get ResolutionCreate object
        assert created_args.reference_id == test_reference.id
        assert created_args.resolver_id == resolver_id


def test_filter_unprocessed_references(test_db, test_references):
    """Test _filter_unprocessed_references filters correctly."""
    mock_resolver = MagicMock()
    mock_resolver.id = "test-resolver-id"

    service = ResolutionService(mock_resolver)
    resolver_id = "test-resolver-id"

    # Mock that first reference is already processed
    def mock_get_by_reference_and_resolver(db, ref_id, res_id):
        if ref_id == test_references[0].id:
            return MagicMock()  # Existing resolution
        return None  # No resolution

    with patch.object(
        ResolutionRepository,
        "get_by_reference_and_resolver",
        side_effect=mock_get_by_reference_and_resolver,
    ):
        result = service._filter_unprocessed_references(
            test_db, test_references, resolver_id
        )
        assert len(result) == len(test_references) - 1
        assert test_references[0] not in result
