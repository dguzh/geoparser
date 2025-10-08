from unittest.mock import MagicMock, patch

from geoparser.db.crud import (
    RecognitionRepository,
    RecognizerRepository,
    ReferenceRepository,
)
from geoparser.services.recognition import RecognitionService


def test_recognition_service_initialization():
    """Test basic initialization of RecognitionService."""
    mock_recognizer = MagicMock()
    mock_recognizer.id = "test-recognizer-id"
    mock_recognizer.name = "test_recognizer"
    mock_recognizer.config = {"param1": "value1"}

    service = RecognitionService(mock_recognizer)
    assert service.recognizer == mock_recognizer
    assert service.recognizer_id == "test-recognizer-id"


def test_ensure_recognizer_record_existing(test_db):
    """Test _ensure_recognizer_record with an existing recognizer."""
    mock_recognizer = MagicMock()
    mock_recognizer.id = "existing-recognizer-id"
    mock_recognizer.name = "test_recognizer"
    mock_recognizer.config = {"param": "value"}

    service = RecognitionService(mock_recognizer)

    with patch("geoparser.services.recognition.Session") as mock_session:
        mock_session.return_value.__enter__.return_value = test_db
        mock_session.return_value.__exit__.return_value = None

        mock_db_recognizer = MagicMock()
        mock_db_recognizer.id = "existing-recognizer-id"

        with patch.object(
            RecognizerRepository,
            "get",
            return_value=mock_db_recognizer,
        ):
            with patch.object(RecognizerRepository, "create") as mock_create:
                service._ensure_recognizer_record()
                # Should not create a new record
                mock_create.assert_not_called()


def test_ensure_recognizer_record_new(test_db):
    """Test _ensure_recognizer_record with a new recognizer."""
    mock_recognizer = MagicMock()
    mock_recognizer.id = "new-recognizer-id"
    mock_recognizer.name = "test_recognizer"
    mock_recognizer.config = {"param": "value"}

    service = RecognitionService(mock_recognizer)

    with patch("geoparser.services.recognition.Session") as mock_session:
        mock_session.return_value.__enter__.return_value = test_db
        mock_session.return_value.__exit__.return_value = None

        with patch.object(RecognizerRepository, "get", return_value=None):
            with patch.object(RecognizerRepository, "create") as mock_create:
                service._ensure_recognizer_record()
                # Should create a new record
                mock_create.assert_called_once()


def test_recognition_service_run_no_documents():
    """Test run with empty document list."""
    mock_recognizer = MagicMock()
    mock_recognizer.id = "test-recognizer-id"

    service = RecognitionService(mock_recognizer)
    service.run([])  # Should return early without error


def test_recognition_service_run_already_processed(test_db, test_documents):
    """Test run with documents already processed by this recognizer."""
    mock_recognizer = MagicMock()
    mock_recognizer.id = "test-recognizer-id"

    service = RecognitionService(mock_recognizer)

    with patch.object(service, "_ensure_recognizer_record"):
        with patch("geoparser.services.recognition.Session") as mock_session:
            mock_session.return_value.__enter__.return_value = test_db
            mock_session.return_value.__exit__.return_value = None

            with patch.object(
                service, "_filter_unprocessed_documents", return_value=[]
            ):
                with patch.object(
                    mock_recognizer, "predict_references"
                ) as mock_predict:
                    service.run(test_documents)
                    mock_predict.assert_not_called()


def test_recognition_service_run_success(test_db, test_documents):
    """Test successful run with unprocessed documents."""
    mock_recognizer = MagicMock()
    mock_recognizer.id = "test-recognizer-id"
    mock_recognizer.predict_references.return_value = [
        [(0, 5), (10, 15)] for _ in test_documents
    ]

    service = RecognitionService(mock_recognizer)

    with patch.object(service, "_ensure_recognizer_record"):
        with patch("geoparser.services.recognition.Session") as mock_session:
            mock_session.return_value.__enter__.return_value = test_db
            mock_session.return_value.__exit__.return_value = None

            with patch.object(
                service, "_filter_unprocessed_documents", return_value=test_documents
            ):
                with patch.object(
                    service, "_record_reference_predictions"
                ) as mock_record:
                    service.run(test_documents)
                    mock_record.assert_called_once_with(
                        test_db,
                        test_documents,
                        [[(0, 5), (10, 15)] for _ in test_documents],
                        service.recognizer_id,
                    )


def test_record_reference_predictions(test_db, test_documents):
    """Test _record_reference_predictions processing."""
    mock_recognizer = MagicMock()
    mock_recognizer.id = "test-recognizer-id"

    service = RecognitionService(mock_recognizer)

    predicted_references = [[(0, 5), (10, 15)] for _ in test_documents]

    with patch.object(service, "_create_reference_record") as mock_create_ref:
        with patch.object(service, "_create_recognition_record") as mock_create_rec:
            service._record_reference_predictions(
                test_db, test_documents, predicted_references, service.recognizer_id
            )

            # Should create references for each document
            for doc in test_documents:
                mock_create_ref.assert_any_call(
                    test_db, doc.id, 0, 5, service.recognizer_id
                )
                mock_create_ref.assert_any_call(
                    test_db, doc.id, 10, 15, service.recognizer_id
                )
                mock_create_rec.assert_any_call(test_db, doc.id, service.recognizer_id)


def test_create_reference_record(test_db, test_document):
    """Test _create_reference_record creates reference with recognizer ID."""
    mock_recognizer = MagicMock()
    mock_recognizer.id = "test-recognizer-id"

    service = RecognitionService(mock_recognizer)

    with patch.object(ReferenceRepository, "create") as mock_create:
        service._create_reference_record(
            test_db, test_document.id, 0, 5, service.recognizer_id
        )

        mock_create.assert_called_once()
        created_args = mock_create.call_args[0][1]  # Get ReferenceCreate object
        assert created_args.start == 0
        assert created_args.end == 5
        assert created_args.document_id == test_document.id
        assert created_args.recognizer_id == service.recognizer_id


def test_create_recognition_record(test_db, test_document):
    """Test _create_recognition_record creates recognition record."""
    mock_recognizer = MagicMock()
    mock_recognizer.id = "test-recognizer-id"

    service = RecognitionService(mock_recognizer)

    with patch.object(RecognitionRepository, "create") as mock_create:
        service._create_recognition_record(
            test_db, test_document.id, service.recognizer_id
        )

        mock_create.assert_called_once()
        created_args = mock_create.call_args[0][1]  # Get RecognitionCreate object
        assert created_args.document_id == test_document.id
        assert created_args.recognizer_id == service.recognizer_id


def test_filter_unprocessed_documents(test_db, test_documents):
    """Test _filter_unprocessed_documents filters correctly."""
    mock_recognizer = MagicMock()
    mock_recognizer.id = "test-recognizer-id"

    service = RecognitionService(mock_recognizer)

    # Mock that first document is already processed
    def mock_get_by_document_and_recognizer(db, doc_id, rec_id):
        if doc_id == test_documents[0].id:
            return MagicMock()  # Existing recognition
        return None  # No recognition

    with patch.object(
        RecognitionRepository,
        "get_by_document_and_recognizer",
        side_effect=mock_get_by_document_and_recognizer,
    ):
        result = service._filter_unprocessed_documents(test_db, test_documents)
        assert len(result) == len(test_documents) - 1
        assert test_documents[0] not in result
