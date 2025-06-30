import uuid
from unittest.mock import MagicMock, patch

import pytest

from geoparser.db.crud import (
    FeatureRepository,
    RecognitionModuleRepository,
    RecognitionObjectRepository,
    RecognitionSubjectRepository,
    ReferenceRepository,
    ReferentRepository,
    ResolutionModuleRepository,
    ResolutionObjectRepository,
    ResolutionSubjectRepository,
)
from geoparser.db.models import RecognitionModule, ResolutionModule
from geoparser.orchestrator import Orchestrator


def test_orchestrator_initialization():
    """Test basic initialization of Orchestrator."""
    orchestrator = Orchestrator()
    assert isinstance(orchestrator, Orchestrator)


def test_initialize_recognition_module_new(test_db, mock_recognition_module):
    """Test _initialize_recognition_module with a new module."""
    orchestrator = Orchestrator()

    # Mock database calls for module creation
    with patch("geoparser.orchestrator.orchestrator.Session") as mock_session:
        mock_session.return_value.__enter__.return_value = test_db
        mock_session.return_value.__exit__.return_value = None
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
    with patch("geoparser.orchestrator.orchestrator.Session") as mock_session:
        mock_session.return_value.__enter__.return_value = test_db
        mock_session.return_value.__exit__.return_value = None
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
    with patch("geoparser.orchestrator.orchestrator.Session") as mock_session:
        mock_session.return_value.__enter__.return_value = test_db
        mock_session.return_value.__exit__.return_value = None
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
    with patch("geoparser.orchestrator.orchestrator.Session") as mock_session:
        mock_session.return_value.__enter__.return_value = test_db
        mock_session.return_value.__exit__.return_value = None
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

    # Create unsupported module (not a Recognizer or Resolver)
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
    with patch("geoparser.orchestrator.orchestrator.Session") as mock_session:
        mock_session.return_value.__enter__.return_value = test_db
        mock_session.return_value.__exit__.return_value = None
        with patch.object(orchestrator, "_get_unprocessed_documents") as mock_get_docs:
            with patch.object(
                orchestrator, "_process_reference_predictions"
            ) as mock_process:
                # Set up mocks
                mock_get_docs.return_value = [test_document]
                mock_recognition_module.predict_references.return_value = [
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
                mock_recognition_module.predict_references.assert_called_once_with(
                    [test_document]
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
    with patch("geoparser.orchestrator.orchestrator.Session") as mock_session:
        mock_session.return_value.__enter__.return_value = test_db
        mock_session.return_value.__exit__.return_value = None
        with patch.object(orchestrator, "_get_unprocessed_documents") as mock_get_docs:
            # Set up mocks
            mock_get_docs.return_value = []

            # Call the method
            orchestrator._execute_recognition_module(
                mock_recognition_module, module_id, test_project.id
            )

            # Verify that recognition module wasn't called due to no documents
            mock_get_docs.assert_called_once_with(test_db, module_id, test_project.id)
            mock_recognition_module.predict_references.assert_not_called()


def test_execute_resolution_module(
    test_db, test_project, mock_resolution_module, test_reference, test_document
):
    """Test _execute_resolution_module with a reference."""
    orchestrator = Orchestrator()
    module_id = uuid.uuid4()

    # Add document reference to the reference for testing
    test_reference.document = test_document

    # Mock private methods and database calls
    with patch("geoparser.orchestrator.orchestrator.Session") as mock_session:
        mock_session.return_value.__enter__.return_value = test_db
        mock_session.return_value.__exit__.return_value = None
        with patch.object(orchestrator, "_get_unprocessed_references") as mock_get_refs:
            with patch.object(
                orchestrator, "_process_referent_predictions"
            ) as mock_process:
                # Set up mocks
                mock_get_refs.return_value = [test_reference]
                mock_resolution_module.predict_referents.return_value = [
                    [("test_gazetteer", "loc1"), ("test_gazetteer", "loc2")]
                ]

                # Call the method
                orchestrator._execute_resolution_module(
                    mock_resolution_module, module_id, test_project.id
                )

                # Verify calls
                mock_get_refs.assert_called_once_with(
                    test_db, module_id, test_project.id
                )
                mock_resolution_module.predict_referents.assert_called_once()
                mock_process.assert_called_once_with(
                    test_db,
                    [test_reference.id],
                    [[("test_gazetteer", "loc1"), ("test_gazetteer", "loc2")]],
                    module_id,
                )


def test_execute_resolution_module_no_references(
    test_db, test_project, mock_resolution_module
):
    """Test _execute_resolution_module with no references."""
    orchestrator = Orchestrator()
    module_id = uuid.uuid4()

    # Mock private methods and database calls
    with patch("geoparser.orchestrator.orchestrator.Session") as mock_session:
        mock_session.return_value.__enter__.return_value = test_db
        mock_session.return_value.__exit__.return_value = None
        with patch.object(orchestrator, "_get_unprocessed_references") as mock_get_refs:
            # Set up mocks
            mock_get_refs.return_value = []

            # Call the method
            orchestrator._execute_resolution_module(
                mock_resolution_module, module_id, test_project.id
            )

            # Verify that resolution module wasn't called due to no references
            mock_get_refs.assert_called_once_with(test_db, module_id, test_project.id)
            mock_resolution_module.predict_referents.assert_not_called()


def test_process_reference_predictions(test_db, mock_recognition_module):
    """Test _process_reference_predictions."""
    orchestrator = Orchestrator()
    module_id = uuid.uuid4()
    document_id = uuid.uuid4()

    # Mock private methods
    with patch.object(orchestrator, "_create_reference_record") as mock_create:
        with patch.object(orchestrator, "_mark_document_processed") as mock_mark:
            # Call the method
            orchestrator._process_reference_predictions(
                test_db, [document_id], [[(0, 5), (10, 15)]], module_id
            )

            # Verify method calls
            mock_create.assert_any_call(test_db, document_id, 0, 5, module_id)
            mock_create.assert_any_call(test_db, document_id, 10, 15, module_id)
            assert mock_create.call_count == 2

            mock_mark.assert_called_once_with(test_db, document_id, module_id)


def test_create_reference_record(test_db, test_document):
    """Test _create_reference_record when reference doesn't exist."""
    orchestrator = Orchestrator()
    module_id = uuid.uuid4()

    # Mock database calls
    with patch.object(
        ReferenceRepository, "get_by_document_and_span", return_value=None
    ) as mock_get:
        with patch.object(ReferenceRepository, "create") as mock_create_reference:
            with patch.object(
                RecognitionObjectRepository, "create"
            ) as mock_create_recognition:
                # Set up mocks
                reference_id = uuid.uuid4()
                reference = MagicMock()
                reference.id = reference_id
                mock_create_reference.return_value = reference

                # Call the method
                result_id = orchestrator._create_reference_record(
                    test_db, test_document.id, 29, 35, module_id
                )

                # Verify calls
                mock_get.assert_called_once_with(test_db, test_document.id, 29, 35)
                mock_create_reference.assert_called_once()
                mock_create_recognition.assert_called_once()
                assert result_id == reference_id


def test_create_reference_record_existing(test_db, test_document, test_reference):
    """Test _create_reference_record when reference already exists."""
    orchestrator = Orchestrator()
    module_id = uuid.uuid4()

    # Mock database calls
    with patch.object(
        ReferenceRepository, "get_by_document_and_span", return_value=test_reference
    ) as mock_get:
        with patch.object(ReferenceRepository, "create") as mock_create_reference:
            with patch.object(
                RecognitionObjectRepository, "create"
            ) as mock_create_recognition:
                # Call the method
                result_id = orchestrator._create_reference_record(
                    test_db, test_document.id, 29, 35, module_id
                )

                # Verify calls
                mock_get.assert_called_once_with(test_db, test_document.id, 29, 35)
                mock_create_reference.assert_not_called()
                mock_create_recognition.assert_called_once()
                assert result_id == test_reference.id


def test_process_referent_predictions(test_db, mock_resolution_module):
    """Test _process_referent_predictions."""
    orchestrator = Orchestrator()
    module_id = uuid.uuid4()
    reference_id = uuid.uuid4()

    # Mock private methods
    with patch.object(orchestrator, "_create_referent_record") as mock_create:
        with patch.object(orchestrator, "_mark_reference_processed") as mock_mark:
            # Call the method
            orchestrator._process_referent_predictions(
                test_db,
                [reference_id],
                [[("test_gazetteer", "loc1"), ("test_gazetteer", "loc2")]],
                module_id,
            )

            # Verify method calls
            mock_create.assert_any_call(
                test_db, reference_id, "test_gazetteer", "loc1", module_id
            )
            mock_create.assert_any_call(
                test_db, reference_id, "test_gazetteer", "loc2", module_id
            )
            assert mock_create.call_count == 2

            mock_mark.assert_called_once_with(test_db, reference_id, module_id)


def test_create_referent_record(test_db, test_reference):
    """Test _create_referent_record."""
    orchestrator = Orchestrator()
    module_id = uuid.uuid4()

    # Mock database calls
    with patch.object(
        FeatureRepository, "get_by_gazetteer_and_identifier"
    ) as mock_get_feature:
        with patch.object(ReferentRepository, "create") as mock_create_referent:
            with patch.object(
                ResolutionObjectRepository, "create"
            ) as mock_create_resolution:
                # Set up mocks
                feature_id = 123456
                feature = MagicMock()
                feature.id = feature_id
                mock_get_feature.return_value = feature

                referent_id = uuid.uuid4()
                referent = MagicMock()
                referent.id = referent_id
                mock_create_referent.return_value = referent

                # Call the method
                result_id = orchestrator._create_referent_record(
                    test_db, test_reference.id, "test_gazetteer", "loc1", module_id
                )

                # Verify calls
                mock_get_feature.assert_called_once_with(
                    test_db, "test_gazetteer", "loc1"
                )
                mock_create_referent.assert_called_once()
                mock_create_resolution.assert_called_once()
                assert result_id == referent_id


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


def test_mark_reference_processed(test_db, test_reference):
    """Test _mark_reference_processed."""
    orchestrator = Orchestrator()
    module_id = uuid.uuid4()

    # Mock database call
    with patch.object(ResolutionSubjectRepository, "create") as mock_create:
        # Call the method
        orchestrator._mark_reference_processed(test_db, test_reference.id, module_id)

        # Verify calls
        mock_create.assert_called_once()
