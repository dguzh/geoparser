import uuid
from unittest.mock import MagicMock, patch

import pytest

from geoparser.db.crud import (
    RecognitionRepository,
    RecognizerRepository,
    ReferenceRepository,
)
from geoparser.modules.recognizers.base import Recognizer


def test_recognizer_initialization():
    """Test basic initialization of Recognizer."""

    class TestRecognizer(Recognizer):
        NAME = "test_recognizer"

        def predict_references(self, documents):
            return [[(0, 5)] for _ in documents]

    with patch.object(TestRecognizer, "_load", return_value=uuid.uuid4()):
        recognizer = TestRecognizer(param1="value1")
        assert recognizer.name == "test_recognizer"
        assert recognizer.config == {"param1": "value1"}
        assert recognizer.id is not None


def test_recognizer_abstract():
    """Test that Recognizer is abstract and requires implementation."""

    # Create a concrete subclass that doesn't implement required methods
    class InvalidRecognizer(Recognizer):
        NAME = "invalid_recognizer"

    # Should raise TypeError when instantiated due to abstract methods
    with pytest.raises(TypeError, match="predict_references"):
        InvalidRecognizer()


def test_recognizer_load_existing(test_db):
    """Test _load with an existing recognizer."""

    class TestRecognizer(Recognizer):
        NAME = "test_recognizer"

        def predict_references(self, documents):
            return [[(0, 5)] for _ in documents]

    # Create existing recognizer in database
    existing_recognizer_id = uuid.uuid4()
    with patch("geoparser.modules.recognizers.base.Session") as mock_session:
        mock_session.return_value.__enter__.return_value = test_db
        mock_session.return_value.__exit__.return_value = None

        mock_db_recognizer = MagicMock()
        mock_db_recognizer.id = existing_recognizer_id

        with patch.object(
            RecognizerRepository,
            "get_by_name_and_config",
            return_value=mock_db_recognizer,
        ):
            recognizer = TestRecognizer(param="value")
            assert recognizer.id == existing_recognizer_id


def test_recognizer_load_new(test_db):
    """Test _load with a new recognizer."""

    class TestRecognizer(Recognizer):
        NAME = "test_recognizer"

        def predict_references(self, documents):
            return [[(0, 5)] for _ in documents]

    new_recognizer_id = uuid.uuid4()
    with patch("geoparser.modules.recognizers.base.Session") as mock_session:
        mock_session.return_value.__enter__.return_value = test_db
        mock_session.return_value.__exit__.return_value = None

        mock_new_recognizer = MagicMock()
        mock_new_recognizer.id = new_recognizer_id

        with patch.object(
            RecognizerRepository, "get_by_name_and_config", return_value=None
        ):
            with patch.object(
                RecognizerRepository, "create", return_value=mock_new_recognizer
            ) as mock_create:
                recognizer = TestRecognizer(param="value")
                assert recognizer.id == new_recognizer_id
                mock_create.assert_called_once()


def test_recognizer_run_no_documents():
    """Test run with empty document list."""

    class TestRecognizer(Recognizer):
        NAME = "test_recognizer"

        def predict_references(self, documents):
            return [[(0, 5)] for _ in documents]

    with patch.object(TestRecognizer, "_load", return_value=uuid.uuid4()):
        recognizer = TestRecognizer()
        recognizer.run([])  # Should return early without error


def test_recognizer_run_already_processed(test_db, test_documents):
    """Test run with documents already processed by this recognizer."""

    class TestRecognizer(Recognizer):
        NAME = "test_recognizer"

        def predict_references(self, documents):
            return [[(0, 5)] for _ in documents]

    recognizer_id = uuid.uuid4()
    with patch.object(TestRecognizer, "_load", return_value=recognizer_id):
        recognizer = TestRecognizer()

        with patch("geoparser.modules.recognizers.base.Session") as mock_session:
            mock_session.return_value.__enter__.return_value = test_db
            mock_session.return_value.__exit__.return_value = None

            with patch.object(
                recognizer, "_filter_unprocessed_documents", return_value=[]
            ):
                with patch.object(recognizer, "predict_references") as mock_predict:
                    recognizer.run(test_documents)
                    mock_predict.assert_not_called()


def test_recognizer_run_success(test_db, test_documents):
    """Test successful run with unprocessed documents."""

    class TestRecognizer(Recognizer):
        NAME = "test_recognizer"

        def predict_references(self, documents):
            return [[(0, 5), (10, 15)] for _ in documents]

    recognizer_id = uuid.uuid4()
    with patch.object(TestRecognizer, "_load", return_value=recognizer_id):
        recognizer = TestRecognizer()

        with patch("geoparser.modules.recognizers.base.Session") as mock_session:
            mock_session.return_value.__enter__.return_value = test_db
            mock_session.return_value.__exit__.return_value = None

            with patch.object(
                recognizer, "_filter_unprocessed_documents", return_value=test_documents
            ):
                with patch.object(
                    recognizer, "_record_reference_predictions"
                ) as mock_record:
                    recognizer.run(test_documents)
                    mock_record.assert_called_once_with(
                        test_db,
                        test_documents,
                        [[(0, 5), (10, 15)] for _ in test_documents],
                        recognizer_id,
                    )


def test_record_reference_predictions(test_db, test_documents):
    """Test _record_reference_predictions processing."""

    class TestRecognizer(Recognizer):
        NAME = "test_recognizer"

        def predict_references(self, documents):
            return [[(0, 5)] for _ in documents]

    recognizer_id = uuid.uuid4()
    with patch.object(TestRecognizer, "_load", return_value=recognizer_id):
        recognizer = TestRecognizer()

        predicted_references = [[(0, 5), (10, 15)] for _ in test_documents]

        with patch.object(recognizer, "_create_reference_record") as mock_create_ref:
            with patch.object(
                recognizer, "_create_recognition_record"
            ) as mock_create_rec:
                recognizer._record_reference_predictions(
                    test_db, test_documents, predicted_references, recognizer_id
                )

                # Should create references for each document
                for doc in test_documents:
                    mock_create_ref.assert_any_call(
                        test_db, doc.id, 0, 5, recognizer_id
                    )
                    mock_create_ref.assert_any_call(
                        test_db, doc.id, 10, 15, recognizer_id
                    )
                    mock_create_rec.assert_any_call(test_db, doc.id, recognizer_id)


def test_create_reference_record(test_db, test_document):
    """Test _create_reference_record creates reference with recognizer ID."""

    class TestRecognizer(Recognizer):
        NAME = "test_recognizer"

        def predict_references(self, documents):
            return [[(0, 5)] for _ in documents]

    recognizer_id = uuid.uuid4()
    with patch.object(TestRecognizer, "_load", return_value=recognizer_id):
        recognizer = TestRecognizer()

        with patch.object(ReferenceRepository, "create") as mock_create:
            recognizer._create_reference_record(
                test_db, test_document.id, 0, 5, recognizer_id
            )

            mock_create.assert_called_once()
            created_args = mock_create.call_args[0][1]  # Get ReferenceCreate object
            assert created_args.start == 0
            assert created_args.end == 5
            assert created_args.document_id == test_document.id
            assert created_args.recognizer_id == recognizer_id


def test_create_recognition_record(test_db, test_document):
    """Test _create_recognition_record creates recognition record."""

    class TestRecognizer(Recognizer):
        NAME = "test_recognizer"

        def predict_references(self, documents):
            return [[(0, 5)] for _ in documents]

    recognizer_id = uuid.uuid4()
    with patch.object(TestRecognizer, "_load", return_value=recognizer_id):
        recognizer = TestRecognizer()

        with patch.object(RecognitionRepository, "create") as mock_create:
            recognizer._create_recognition_record(
                test_db, test_document.id, recognizer_id
            )

            mock_create.assert_called_once()
            created_args = mock_create.call_args[0][1]  # Get RecognitionCreate object
            assert created_args.document_id == test_document.id
            assert created_args.recognizer_id == recognizer_id


def test_filter_unprocessed_documents(test_db, test_documents):
    """Test _filter_unprocessed_documents filters correctly."""

    class TestRecognizer(Recognizer):
        NAME = "test_recognizer"

        def predict_references(self, documents):
            return [[(0, 5)] for _ in documents]

    recognizer_id = uuid.uuid4()
    with patch.object(TestRecognizer, "_load", return_value=recognizer_id):
        recognizer = TestRecognizer()

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
            result = recognizer._filter_unprocessed_documents(test_db, test_documents)
            assert len(result) == len(test_documents) - 1
            assert test_documents[0] not in result


def test_predict_references_implementation():
    """Test a valid implementation of predict_references."""

    class ValidRecognizer(Recognizer):
        NAME = "valid_recognizer"

        def predict_references(self, documents):
            return [[(0, 5), (10, 15)] for _ in documents]

    with patch.object(ValidRecognizer, "_load", return_value=uuid.uuid4()):
        recognizer = ValidRecognizer()

        # Create mock Document objects
        doc1 = MagicMock()
        doc1.text = "Test document 1"
        doc2 = MagicMock()
        doc2.text = "Test document 2"
        documents = [doc1, doc2]

        result = recognizer.predict_references(documents)
        assert len(result) == 2
        assert result[0] == [(0, 5), (10, 15)]
        assert result[1] == [(0, 5), (10, 15)]
