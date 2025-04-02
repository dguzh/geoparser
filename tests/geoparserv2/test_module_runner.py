import uuid
from unittest.mock import MagicMock, call, patch

import pytest

from geoparser.db.crud import (
    LocationRepository,
    RecognitionModuleRepository,
    RecognitionObjectRepository,
    RecognitionSubjectRepository,
    ResolutionModuleRepository,
    ResolutionObjectRepository,
    ResolutionSubjectRepository,
    ToponymRepository,
)
from geoparser.db.models import RecognitionModule as RecognitionModuleModel
from geoparser.db.models import ResolutionModule as ResolutionModuleModel
from geoparser.geoparserv2.module_runner import ModuleRunner


def test_module_runner_initialization():
    """Test basic initialization of ModuleRunner."""
    runner = ModuleRunner()
    assert isinstance(runner, ModuleRunner)


def test_initialize_recognition_module_new(test_db, mock_recognition_module):
    """Test _initialize_recognition_module with a new module."""
    runner = ModuleRunner()

    # Mock database calls for module creation
    with patch(
        "geoparser.geoparserv2.module_runner.get_db", return_value=iter([test_db])
    ):
        with patch.object(
            RecognitionModuleRepository, "get_by_name_and_config", return_value=None
        ) as mock_get:
            new_module = RecognitionModuleModel(
                id=uuid.uuid4(), name="mock_recognition", config={"param": "value"}
            )
            with patch.object(
                RecognitionModuleRepository, "create", return_value=new_module
            ) as mock_create:
                # Call the method
                module_id = runner._initialize_recognition_module(
                    mock_recognition_module
                )

                # Verify calls
                mock_get.assert_called_once_with(
                    test_db,
                    mock_recognition_module.name,
                    mock_recognition_module.config,
                )
                mock_create.assert_called_once()
                assert module_id == new_module.id


def test_initialize_recognition_module_existing(test_db, mock_recognition_module):
    """Test _initialize_recognition_module with an existing module."""
    runner = ModuleRunner()

    # Create existing module in database
    existing_module = RecognitionModuleModel(
        id=uuid.uuid4(), name="mock_recognition", config={"param": "value"}
    )

    # Mock database calls
    with patch(
        "geoparser.geoparserv2.module_runner.get_db", return_value=iter([test_db])
    ):
        with patch.object(
            RecognitionModuleRepository,
            "get_by_name_and_config",
            return_value=existing_module,
        ) as mock_get:
            # Call the method
            module_id = runner._initialize_recognition_module(mock_recognition_module)

            # Verify calls
            mock_get.assert_called_once_with(
                test_db, mock_recognition_module.name, mock_recognition_module.config
            )
            assert module_id == existing_module.id


def test_initialize_resolution_module_new(test_db, mock_resolution_module):
    """Test _initialize_resolution_module with a new module."""
    runner = ModuleRunner()

    # Mock database calls for module creation
    with patch(
        "geoparser.geoparserv2.module_runner.get_db", return_value=iter([test_db])
    ):
        with patch.object(
            ResolutionModuleRepository, "get_by_name_and_config", return_value=None
        ) as mock_get:
            new_module = ResolutionModuleModel(
                id=uuid.uuid4(), name="mock_resolution", config={"param": "value"}
            )
            with patch.object(
                ResolutionModuleRepository, "create", return_value=new_module
            ) as mock_create:
                # Call the method
                module_id = runner._initialize_resolution_module(mock_resolution_module)

                # Verify calls
                mock_get.assert_called_once_with(
                    test_db, mock_resolution_module.name, mock_resolution_module.config
                )
                mock_create.assert_called_once()
                assert module_id == new_module.id


def test_initialize_resolution_module_existing(test_db, mock_resolution_module):
    """Test _initialize_resolution_module with an existing module."""
    runner = ModuleRunner()

    # Create existing module in database
    existing_module = ResolutionModuleModel(
        id=uuid.uuid4(), name="mock_resolution", config={"param": "value"}
    )

    # Mock database calls
    with patch(
        "geoparser.geoparserv2.module_runner.get_db", return_value=iter([test_db])
    ):
        with patch.object(
            ResolutionModuleRepository,
            "get_by_name_and_config",
            return_value=existing_module,
        ) as mock_get:
            # Call the method
            module_id = runner._initialize_resolution_module(mock_resolution_module)

            # Verify calls
            mock_get.assert_called_once_with(
                test_db, mock_resolution_module.name, mock_resolution_module.config
            )
            assert module_id == existing_module.id


def test_run_module_recognition(test_db, test_project, mock_recognition_module):
    """Test run_module with a recognition module."""
    runner = ModuleRunner()

    # Mock private methods
    with patch.object(runner, "_initialize_recognition_module") as mock_init:
        with patch.object(runner, "_execute_recognition_module") as mock_exec:
            # Set up mocks
            module_id = uuid.uuid4()
            mock_init.return_value = module_id

            # Call run_module
            runner.run_module(mock_recognition_module, test_project.id)

            # Verify method calls
            mock_init.assert_called_once_with(mock_recognition_module)
            mock_exec.assert_called_once_with(
                mock_recognition_module, module_id, test_project.id
            )


def test_run_module_resolution(test_db, test_project, mock_resolution_module):
    """Test run_module with a resolution module."""
    runner = ModuleRunner()

    # Mock private methods
    with patch.object(runner, "_initialize_resolution_module") as mock_init:
        with patch.object(runner, "_execute_resolution_module") as mock_exec:
            # Set up mocks
            module_id = uuid.uuid4()
            mock_init.return_value = module_id

            # Call run_module
            runner.run_module(mock_resolution_module, test_project.id)

            # Verify method calls
            mock_init.assert_called_once_with(mock_resolution_module)
            mock_exec.assert_called_once_with(
                mock_resolution_module, module_id, test_project.id
            )


def test_run_module_unsupported_type(test_db, test_project):
    """Test run_module with an unsupported module type."""
    runner = ModuleRunner()

    # Create unsupported module (not a RecognitionModule or ResolutionModule)
    unsupported_module = MagicMock()

    # Call run_module and expect error
    with pytest.raises(ValueError, match="Unsupported module type"):
        runner.run_module(unsupported_module, test_project.id)


def test_execute_recognition_module(
    test_db, test_project, mock_recognition_module, test_document
):
    """Test _execute_recognition_module with a document."""
    runner = ModuleRunner()
    module_id = uuid.uuid4()

    # Mock private methods and database calls
    with patch(
        "geoparser.geoparserv2.module_runner.get_db", return_value=iter([test_db])
    ):
        with patch.object(runner, "_get_unprocessed_documents") as mock_get_docs:
            with patch.object(runner, "_process_toponym_predictions") as mock_process:
                # Set up mocks
                mock_get_docs.return_value = [test_document]

                # Call _execute_recognition_module
                runner._execute_recognition_module(
                    mock_recognition_module, module_id, test_project.id
                )

                # Verify method calls
                mock_get_docs.assert_called_once_with(
                    test_db, module_id, test_project.id
                )
                mock_recognition_module.predict_toponyms.assert_called_once_with(
                    [test_document.text]
                )
                mock_process.assert_called_once_with(
                    test_db,
                    [test_document.id],
                    mock_recognition_module.predict_toponyms.return_value,
                    module_id,
                )


def test_execute_recognition_module_no_documents(
    test_db, test_project, mock_recognition_module
):
    """Test _execute_recognition_module with no unprocessed documents."""
    runner = ModuleRunner()
    module_id = uuid.uuid4()

    # Mock private methods and database calls
    with patch(
        "geoparser.geoparserv2.module_runner.get_db", return_value=iter([test_db])
    ):
        with patch.object(runner, "_get_unprocessed_documents") as mock_get_docs:
            # Set up mocks
            mock_get_docs.return_value = []

            # Call _execute_recognition_module
            runner._execute_recognition_module(
                mock_recognition_module, module_id, test_project.id
            )

            # Verify method calls
            mock_get_docs.assert_called_once_with(test_db, module_id, test_project.id)
            mock_recognition_module.predict_toponyms.assert_not_called()


def test_execute_resolution_module(
    test_db, test_project, mock_resolution_module, test_toponym, test_document
):
    """Test _execute_resolution_module with a toponym."""
    runner = ModuleRunner()
    module_id = uuid.uuid4()

    # Ensure toponym has access to its document (for test setup)
    test_toponym.document = test_document

    # Mock private methods and database calls
    with patch(
        "geoparser.geoparserv2.module_runner.get_db", return_value=iter([test_db])
    ):
        with patch.object(runner, "_get_unprocessed_toponyms") as mock_get_tops:
            with patch.object(runner, "_process_location_predictions") as mock_process:
                # Set up mocks
                mock_get_tops.return_value = [test_toponym]

                # Call _execute_resolution_module
                runner._execute_resolution_module(
                    mock_resolution_module, module_id, test_project.id
                )

                # Verify method calls
                mock_get_tops.assert_called_once_with(
                    test_db, module_id, test_project.id
                )
                mock_resolution_module.predict_locations.assert_called_once()
                mock_process.assert_called_once_with(
                    test_db,
                    [test_toponym.id],
                    mock_resolution_module.predict_locations.return_value,
                    module_id,
                )


def test_execute_resolution_module_no_toponyms(
    test_db, test_project, mock_resolution_module
):
    """Test _execute_resolution_module with no unprocessed toponyms."""
    runner = ModuleRunner()
    module_id = uuid.uuid4()

    # Mock private methods and database calls
    with patch(
        "geoparser.geoparserv2.module_runner.get_db", return_value=iter([test_db])
    ):
        with patch.object(runner, "_get_unprocessed_toponyms") as mock_get_tops:
            # Set up mocks
            mock_get_tops.return_value = []

            # Call _execute_resolution_module
            runner._execute_resolution_module(
                mock_resolution_module, module_id, test_project.id
            )

            # Verify method calls
            mock_get_tops.assert_called_once_with(test_db, module_id, test_project.id)
            mock_resolution_module.predict_locations.assert_not_called()


def test_process_toponym_predictions(test_db, mock_recognition_module):
    """Test _process_toponym_predictions."""
    runner = ModuleRunner()
    module_id = uuid.uuid4()
    document_ids = [uuid.uuid4()]
    predicted_toponyms = [[(10, 15), (20, 25)]]

    # Mock private methods
    with patch.object(runner, "_create_toponym_record") as mock_create:
        with patch.object(runner, "_mark_document_processed") as mock_mark:
            # Call _process_toponym_predictions
            runner._process_toponym_predictions(
                test_db, document_ids, predicted_toponyms, module_id
            )

            # Verify method calls
            assert mock_create.call_count == 2
            mock_create.assert_has_calls(
                [
                    call(test_db, document_ids[0], 10, 15, module_id),
                    call(test_db, document_ids[0], 20, 25, module_id),
                ]
            )
            mock_mark.assert_called_once_with(test_db, document_ids[0], module_id)


def test_create_toponym_record(test_db, test_document):
    """Test _create_toponym_record."""
    runner = ModuleRunner()
    module_id = uuid.uuid4()

    # Mock repository calls
    with patch.object(ToponymRepository, "create") as mock_create_toponym:
        with patch.object(RecognitionObjectRepository, "create") as mock_create_object:
            # Set up mocks
            toponym_id = uuid.uuid4()
            toponym = MagicMock()
            toponym.id = toponym_id
            mock_create_toponym.return_value = toponym

            # Call _create_toponym_record
            result = runner._create_toponym_record(
                test_db, test_document.id, 10, 15, module_id
            )

            # Verify method calls and result
            mock_create_toponym.assert_called_once()
            mock_create_object.assert_called_once()
            assert result == toponym_id


def test_process_location_predictions(test_db, mock_resolution_module):
    """Test _process_location_predictions."""
    runner = ModuleRunner()
    module_id = uuid.uuid4()
    toponym_ids = [uuid.uuid4()]
    predicted_locations = [[("loc1", 0.8), ("loc2", 0.6)]]

    # Mock private methods
    with patch.object(runner, "_create_location_record") as mock_create:
        with patch.object(runner, "_mark_toponym_processed") as mock_mark:
            # Call _process_location_predictions
            runner._process_location_predictions(
                test_db, toponym_ids, predicted_locations, module_id
            )

            # Verify method calls
            assert mock_create.call_count == 2
            mock_create.assert_has_calls(
                [
                    call(test_db, toponym_ids[0], "loc1", 0.8, module_id),
                    call(test_db, toponym_ids[0], "loc2", 0.6, module_id),
                ]
            )
            mock_mark.assert_called_once_with(test_db, toponym_ids[0], module_id)


def test_create_location_record(test_db, test_toponym):
    """Test _create_location_record."""
    runner = ModuleRunner()
    module_id = uuid.uuid4()

    # Mock repository calls
    with patch.object(LocationRepository, "create") as mock_create_location:
        with patch.object(ResolutionObjectRepository, "create") as mock_create_object:
            # Set up mocks
            location_id = uuid.uuid4()
            location = MagicMock()
            location.id = location_id
            mock_create_location.return_value = location

            # Call _create_location_record
            result = runner._create_location_record(
                test_db, test_toponym.id, "loc1", 0.8, module_id
            )

            # Verify method calls and result
            mock_create_location.assert_called_once()
            mock_create_object.assert_called_once()
            assert result == location_id


def test_mark_document_processed(test_db, test_document):
    """Test _mark_document_processed."""
    runner = ModuleRunner()
    module_id = uuid.uuid4()

    # Mock repository calls
    with patch.object(RecognitionSubjectRepository, "create") as mock_create:
        # Call _mark_document_processed
        runner._mark_document_processed(test_db, test_document.id, module_id)

        # Verify method calls
        mock_create.assert_called_once()


def test_mark_toponym_processed(test_db, test_toponym):
    """Test _mark_toponym_processed."""
    runner = ModuleRunner()
    module_id = uuid.uuid4()

    # Mock repository calls
    with patch.object(ResolutionSubjectRepository, "create") as mock_create:
        # Call _mark_toponym_processed
        runner._mark_toponym_processed(test_db, test_toponym.id, module_id)

        # Verify method calls
        mock_create.assert_called_once()
