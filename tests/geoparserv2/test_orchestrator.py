import uuid
from unittest.mock import MagicMock, patch

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
from geoparser.db.models import RecognitionModule, ResolutionModule
from geoparser.geoparserv2.orchestrator import Orchestrator


def test_orchestrator_initialization():
    """Test basic initialization of Orchestrator."""
    orchestrator = Orchestrator()
    assert isinstance(orchestrator, Orchestrator)


def test_initialize_recognition_module_new(test_db, mock_recognition_module):
    """Test _initialize_recognition_module with a new module."""
    orchestrator = Orchestrator()

    # Mock database calls for module creation
    with patch(
        "geoparser.geoparserv2.orchestrator.get_db", return_value=iter([test_db])
    ):
        with patch.object(
            RecognitionModuleRepository, "get_by_name_and_config", return_value=None
        ) as mock_get:
            new_module = RecognitionModule(
                id=uuid.uuid4(), name="mock_recognition", config={"param": "value"}
            )
            with patch.object(
                RecognitionModuleRepository, "create", return_value=new_module
            ) as mock_create:
                # Call the method
                module_id = orchestrator._initialize_recognition_module(
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
    orchestrator = Orchestrator()

    # Create existing module in database
    existing_module = RecognitionModule(
        id=uuid.uuid4(), name="mock_recognition", config={"param": "value"}
    )

    # Mock database calls
    with patch(
        "geoparser.geoparserv2.orchestrator.get_db", return_value=iter([test_db])
    ):
        with patch.object(
            RecognitionModuleRepository,
            "get_by_name_and_config",
            return_value=existing_module,
        ) as mock_get:
            # Call the method
            module_id = orchestrator._initialize_recognition_module(
                mock_recognition_module
            )

            # Verify calls
            mock_get.assert_called_once_with(
                test_db, mock_recognition_module.name, mock_recognition_module.config
            )
            assert module_id == existing_module.id


def test_initialize_resolution_module_new(test_db, mock_resolution_module):
    """Test _initialize_resolution_module with a new module."""
    orchestrator = Orchestrator()

    # Mock database calls for module creation
    with patch(
        "geoparser.geoparserv2.orchestrator.get_db", return_value=iter([test_db])
    ):
        with patch.object(
            ResolutionModuleRepository, "get_by_name_and_config", return_value=None
        ) as mock_get:
            new_module = ResolutionModule(
                id=uuid.uuid4(), name="mock_resolution", config={"param": "value"}
            )
            with patch.object(
                ResolutionModuleRepository, "create", return_value=new_module
            ) as mock_create:
                # Call the method
                module_id = orchestrator._initialize_resolution_module(
                    mock_resolution_module
                )

                # Verify calls
                mock_get.assert_called_once_with(
                    test_db, mock_resolution_module.name, mock_resolution_module.config
                )
                mock_create.assert_called_once()
                assert module_id == new_module.id


def test_initialize_resolution_module_existing(test_db, mock_resolution_module):
    """Test _initialize_resolution_module with an existing module."""
    orchestrator = Orchestrator()

    # Create existing module in database
    existing_module = ResolutionModule(
        id=uuid.uuid4(), name="mock_resolution", config={"param": "value"}
    )

    # Mock database calls
    with patch(
        "geoparser.geoparserv2.orchestrator.get_db", return_value=iter([test_db])
    ):
        with patch.object(
            ResolutionModuleRepository,
            "get_by_name_and_config",
            return_value=existing_module,
        ) as mock_get:
            # Call the method
            module_id = orchestrator._initialize_resolution_module(
                mock_resolution_module
            )

            # Verify calls
            mock_get.assert_called_once_with(
                test_db, mock_resolution_module.name, mock_resolution_module.config
            )
            assert module_id == existing_module.id


def test_run_module_recognition(test_db, test_project, mock_recognition_module):
    """Test run_module with a recognition module."""
    orchestrator = Orchestrator()

    # Mock private methods
    with patch.object(orchestrator, "_initialize_recognition_module") as mock_init:
        with patch.object(orchestrator, "_execute_recognition_module") as mock_exec:
            # Set up mocks
            module_id = uuid.uuid4()
            mock_init.return_value = module_id

            # Call run_module
            orchestrator.run_module(mock_recognition_module, test_project.id)

            # Verify method calls
            mock_init.assert_called_once_with(mock_recognition_module)
            mock_exec.assert_called_once_with(
                mock_recognition_module, module_id, test_project.id
            )


def test_run_module_resolution(test_db, test_project, mock_resolution_module):
    """Test run_module with a resolution module."""
    orchestrator = Orchestrator()

    # Mock private methods
    with patch.object(orchestrator, "_initialize_resolution_module") as mock_init:
        with patch.object(orchestrator, "_execute_resolution_module") as mock_exec:
            # Set up mocks
            module_id = uuid.uuid4()
            mock_init.return_value = module_id

            # Call run_module
            orchestrator.run_module(mock_resolution_module, test_project.id)

            # Verify method calls
            mock_init.assert_called_once_with(mock_resolution_module)
            mock_exec.assert_called_once_with(
                mock_resolution_module, module_id, test_project.id
            )


def test_run_module_unsupported_type(test_db, test_project):
    """Test run_module with an unsupported module type."""
    orchestrator = Orchestrator()

    # Create unsupported module (not a AbstractRecognitionModule or AbstractResolutionModule)
    unsupported_module = MagicMock()

    # Call run_module and expect error
    with pytest.raises(ValueError, match="Unsupported module type"):
        orchestrator.run_module(unsupported_module, test_project.id)


def test_execute_recognition_module(
    test_db, test_project, mock_recognition_module, test_document
):
    """Test _execute_recognition_module with a document."""
    orchestrator = Orchestrator()
    module_id = uuid.uuid4()

    # Mock private methods and database calls
    with patch(
        "geoparser.geoparserv2.orchestrator.get_db", return_value=iter([test_db])
    ):
        with patch.object(orchestrator, "_get_unprocessed_documents") as mock_get_docs:
            with patch.object(
                orchestrator, "_process_toponym_predictions"
            ) as mock_process:
                # Set up mocks
                mock_get_docs.return_value = [test_document]
                mock_recognition_module.predict_toponyms.return_value = [
                    [(0, 5), (10, 15)]
                ]

                # Call the method
                orchestrator._execute_recognition_module(
                    mock_recognition_module, module_id, test_project.id
                )

                # Verify calls
                mock_get_docs.assert_called_once_with(
                    test_db, module_id, test_project.id
                )
                mock_recognition_module.predict_toponyms.assert_called_once_with(
                    [test_document.text]
                )
                mock_process.assert_called_once_with(
                    test_db, [test_document.id], [[(0, 5), (10, 15)]], module_id
                )


def test_execute_recognition_module_no_documents(
    test_db, test_project, mock_recognition_module
):
    """Test _execute_recognition_module with no documents."""
    orchestrator = Orchestrator()
    module_id = uuid.uuid4()

    # Mock private methods and database calls
    with patch(
        "geoparser.geoparserv2.orchestrator.get_db", return_value=iter([test_db])
    ):
        with patch.object(orchestrator, "_get_unprocessed_documents") as mock_get_docs:
            # Set up mocks
            mock_get_docs.return_value = []

            # Call the method
            orchestrator._execute_recognition_module(
                mock_recognition_module, module_id, test_project.id
            )

            # Verify that recognition module wasn't called due to no documents
            mock_get_docs.assert_called_once_with(test_db, module_id, test_project.id)
            mock_recognition_module.predict_toponyms.assert_not_called()


def test_execute_resolution_module(
    test_db, test_project, mock_resolution_module, test_toponym, test_document
):
    """Test _execute_resolution_module with a toponym."""
    orchestrator = Orchestrator()
    module_id = uuid.uuid4()

    # Add document reference to the toponym for testing
    test_toponym.document = test_document

    # Mock private methods and database calls
    with patch(
        "geoparser.geoparserv2.orchestrator.get_db", return_value=iter([test_db])
    ):
        with patch.object(orchestrator, "_get_unprocessed_toponyms") as mock_get_topo:
            with patch.object(
                orchestrator, "_process_location_predictions"
            ) as mock_process:
                # Set up mocks
                mock_get_topo.return_value = [test_toponym]
                mock_resolution_module.predict_locations.return_value = [
                    [("loc1", 0.8), ("loc2", 0.6)]
                ]

                # Call the method
                orchestrator._execute_resolution_module(
                    mock_resolution_module, module_id, test_project.id
                )

                # Verify calls
                mock_get_topo.assert_called_once_with(
                    test_db, module_id, test_project.id
                )
                mock_resolution_module.predict_locations.assert_called_once()
                mock_process.assert_called_once_with(
                    test_db,
                    [test_toponym.id],
                    [[("loc1", 0.8), ("loc2", 0.6)]],
                    module_id,
                )


def test_execute_resolution_module_no_toponyms(
    test_db, test_project, mock_resolution_module
):
    """Test _execute_resolution_module with no toponyms."""
    orchestrator = Orchestrator()
    module_id = uuid.uuid4()

    # Mock private methods and database calls
    with patch(
        "geoparser.geoparserv2.orchestrator.get_db", return_value=iter([test_db])
    ):
        with patch.object(orchestrator, "_get_unprocessed_toponyms") as mock_get_topo:
            # Set up mocks
            mock_get_topo.return_value = []

            # Call the method
            orchestrator._execute_resolution_module(
                mock_resolution_module, module_id, test_project.id
            )

            # Verify that resolution module wasn't called due to no toponyms
            mock_get_topo.assert_called_once_with(test_db, module_id, test_project.id)
            mock_resolution_module.predict_locations.assert_not_called()


def test_process_toponym_predictions(test_db, mock_recognition_module):
    """Test _process_toponym_predictions."""
    orchestrator = Orchestrator()
    module_id = uuid.uuid4()
    document_id = uuid.uuid4()

    # Mock private methods
    with patch.object(orchestrator, "_create_toponym_record") as mock_create:
        with patch.object(orchestrator, "_mark_document_processed") as mock_mark:
            # Call the method
            orchestrator._process_toponym_predictions(
                test_db, [document_id], [[(0, 5), (10, 15)]], module_id
            )

            # Verify method calls
            mock_create.assert_any_call(test_db, document_id, 0, 5, module_id)
            mock_create.assert_any_call(test_db, document_id, 10, 15, module_id)
            assert mock_create.call_count == 2

            mock_mark.assert_called_once_with(test_db, document_id, module_id)


def test_create_toponym_record(test_db, test_document):
    """Test _create_toponym_record when toponym doesn't exist."""
    orchestrator = Orchestrator()
    module_id = uuid.uuid4()

    # Mock database calls
    with patch.object(
        ToponymRepository, "get_by_document_and_span", return_value=None
    ) as mock_get:
        with patch.object(ToponymRepository, "create") as mock_create_toponym:
            with patch.object(
                RecognitionObjectRepository, "create"
            ) as mock_create_recognition:
                # Set up mocks
                toponym_id = uuid.uuid4()
                toponym = MagicMock()
                toponym.id = toponym_id
                mock_create_toponym.return_value = toponym

                # Call the method
                result_id = orchestrator._create_toponym_record(
                    test_db, test_document.id, 10, 15, module_id
                )

                # Verify calls
                mock_get.assert_called_once_with(test_db, test_document.id, 10, 15)
                mock_create_toponym.assert_called_once()
                mock_create_recognition.assert_called_once()
                assert result_id == toponym_id


def test_create_toponym_record_existing(test_db, test_document, test_toponym):
    """Test _create_toponym_record when toponym already exists."""
    orchestrator = Orchestrator()
    module_id = uuid.uuid4()

    # Mock database calls
    with patch.object(
        ToponymRepository, "get_by_document_and_span", return_value=test_toponym
    ) as mock_get:
        with patch.object(ToponymRepository, "create") as mock_create_toponym:
            with patch.object(
                RecognitionObjectRepository, "create"
            ) as mock_create_recognition:
                # Call the method
                result_id = orchestrator._create_toponym_record(
                    test_db, test_document.id, 27, 33, module_id
                )

                # Verify calls
                mock_get.assert_called_once_with(test_db, test_document.id, 27, 33)
                mock_create_toponym.assert_not_called()
                mock_create_recognition.assert_called_once()
                assert result_id == test_toponym.id


def test_process_location_predictions(test_db, mock_resolution_module):
    """Test _process_location_predictions."""
    orchestrator = Orchestrator()
    module_id = uuid.uuid4()
    toponym_id = uuid.uuid4()

    # Mock private methods
    with patch.object(orchestrator, "_create_location_record") as mock_create:
        with patch.object(orchestrator, "_mark_toponym_processed") as mock_mark:
            # Call the method
            orchestrator._process_location_predictions(
                test_db,
                [toponym_id],
                [[("loc1", 0.8), ("loc2", 0.6)]],
                module_id,
            )

            # Verify method calls
            mock_create.assert_any_call(test_db, toponym_id, "loc1", 0.8, module_id)
            mock_create.assert_any_call(test_db, toponym_id, "loc2", 0.6, module_id)
            assert mock_create.call_count == 2

            mock_mark.assert_called_once_with(test_db, toponym_id, module_id)


def test_create_location_record(test_db, test_toponym):
    """Test _create_location_record."""
    orchestrator = Orchestrator()
    module_id = uuid.uuid4()

    # Mock database calls
    with patch.object(LocationRepository, "create") as mock_create_location:
        with patch.object(
            ResolutionObjectRepository, "create"
        ) as mock_create_resolution:
            # Set up mocks
            location_id = uuid.uuid4()
            location = MagicMock()
            location.id = location_id
            mock_create_location.return_value = location

            # Call the method
            result_id = orchestrator._create_location_record(
                test_db, test_toponym.id, "loc1", 0.8, module_id
            )

            # Verify calls
            mock_create_location.assert_called_once()
            mock_create_resolution.assert_called_once()
            assert result_id == location_id


def test_mark_document_processed(test_db, test_document):
    """Test _mark_document_processed."""
    orchestrator = Orchestrator()
    module_id = uuid.uuid4()

    # Mock database call
    with patch.object(RecognitionSubjectRepository, "create") as mock_create:
        # Call the method
        orchestrator._mark_document_processed(test_db, test_document.id, module_id)

        # Verify calls
        mock_create.assert_called_once()


def test_mark_toponym_processed(test_db, test_toponym):
    """Test _mark_toponym_processed."""
    orchestrator = Orchestrator()
    module_id = uuid.uuid4()

    # Mock database call
    with patch.object(ResolutionSubjectRepository, "create") as mock_create:
        # Call the method
        orchestrator._mark_toponym_processed(test_db, test_toponym.id, module_id)

        # Verify calls
        mock_create.assert_called_once()
