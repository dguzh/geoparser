import uuid
from unittest.mock import MagicMock, patch

from sqlmodel import Session

from geoparser.db.crud import DocumentRepository, ProjectRepository
from geoparser.db.models import Document, Project
from geoparser.geoparserv2.geoparserv2 import GeoparserV2
from geoparser.geoparserv2.modules.interfaces import BaseModule


def test_initialize_project_existing(test_db: Session, test_project: Project):
    """Test _initialize_project with an existing project."""
    geoparser = GeoparserV2.__new__(
        GeoparserV2
    )  # Create instance without calling __init__

    # Mock ProjectRepository.get_by_name to return the test project
    with patch(
        "geoparser.geoparserv2.geoparserv2.ProjectRepository.get_by_name",
        return_value=test_project,
    ):
        with patch(
            "geoparser.geoparserv2.geoparserv2.get_db",
            return_value=iter([test_db]),
        ):
            project_id = geoparser._initialize_project(test_project.name)

            # Verify the correct project id was returned
            assert project_id == test_project.id


def test_initialize_project_new(test_db: Session):
    """Test _initialize_project with a new project."""
    geoparser = GeoparserV2.__new__(
        GeoparserV2
    )  # Create instance without calling __init__

    # Mock ProjectRepository.get_by_name to return None (project doesn't exist)
    with patch(
        "geoparser.geoparserv2.geoparserv2.ProjectRepository.get_by_name",
        return_value=None,
    ):
        # Mock ProjectRepository.create to return a new project
        new_project = Project(name="new-project", id=uuid.uuid4())
        with patch(
            "geoparser.geoparserv2.geoparserv2.ProjectRepository.create",
            return_value=new_project,
        ):
            with patch(
                "geoparser.geoparserv2.geoparserv2.get_db",
                return_value=iter([test_db]),
            ):
                with patch(
                    "geoparser.geoparserv2.geoparserv2.logging.info"
                ) as mock_log:
                    project_id = geoparser._initialize_project("new-project")

                    # Verify logging was called
                    mock_log.assert_called_once()
                    assert (
                        "No project found with name 'new-project'"
                        in mock_log.call_args[0][0]
                    )

                    # Verify the correct project id was returned
                    assert project_id == new_project.id


def test_init_with_existing_project(geoparser_with_existing_project, test_project):
    """Test initializing GeoparserV2 with an existing project."""
    geoparser = geoparser_with_existing_project

    assert geoparser.project_id is not None
    assert geoparser.project_id == test_project.id
    assert geoparser.project_name == test_project.name


def test_init_with_new_project(geoparser_with_new_project, test_db):
    """Test initializing GeoparserV2 with a new project name."""
    geoparser = geoparser_with_new_project

    assert geoparser.project_id is not None
    assert geoparser.project_name == "new-test-project"

    # Verify it was saved to the database
    db_project = ProjectRepository.get_by_name(test_db, "new-test-project")
    assert db_project is not None
    assert db_project.name == "new-test-project"


def test_init_with_no_project_name(test_db):
    """Test initializing GeoparserV2 without providing a project name."""
    # Mock get_db to return the test database
    with patch(
        "geoparser.geoparserv2.geoparserv2.get_db", return_value=iter([test_db])
    ):
        with patch(
            "uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")
        ):
            geoparser = GeoparserV2()

            # Verify that a temporary project name was generated
            assert geoparser.project_name.startswith("temp_project_")
            assert "12345678-1234-5678-1234-567812345678" in geoparser.project_name

            # Verify that a project was created in the database
            db_project = ProjectRepository.get_by_name(test_db, geoparser.project_name)
            assert db_project is not None
            assert db_project.name == geoparser.project_name


def test_add_documents_single(test_db, geoparser_with_existing_project):
    """Test adding a single document."""
    geoparser = geoparser_with_existing_project

    # Patch the get_db function to return a fresh iterator each time
    with patch(
        "geoparser.geoparserv2.geoparserv2.get_db", return_value=iter([test_db])
    ):
        # Add a single document
        document_ids = geoparser.add_documents("This is a test document.")

        # Verify the document was created
        assert len(document_ids) == 1

        # Verify it was saved to the database
        document = test_db.get(Document, document_ids[0])
        assert document is not None
        assert document.text == "This is a test document."
        assert document.project_id == geoparser.project_id


def test_add_documents_multiple(test_db, geoparser_with_existing_project):
    """Test adding multiple documents."""
    geoparser = geoparser_with_existing_project

    # Patch the get_db function to return a fresh iterator each time
    with patch(
        "geoparser.geoparserv2.geoparserv2.get_db", return_value=iter([test_db])
    ):
        # Add multiple documents
        texts = [
            "This is the first test document.",
            "This is the second test document.",
            "This is the third test document.",
        ]
        document_ids = geoparser.add_documents(texts)

        # Verify the documents were created
        assert len(document_ids) == 3

        # Verify they were saved to the database
        for i, doc_id in enumerate(document_ids):
            document = test_db.get(Document, doc_id)
            assert document is not None
            assert document.text == texts[i]
            assert document.project_id == geoparser.project_id

        # Verify we can retrieve all documents for the project
        documents = DocumentRepository.get_by_project(test_db, geoparser.project_id)
        assert len(documents) == 3


def test_get_documents_all(test_db, geoparser_with_existing_project):
    """Test retrieving all documents for a project."""
    geoparser = geoparser_with_existing_project

    # Add multiple documents with one mock
    with patch(
        "geoparser.geoparserv2.geoparserv2.get_db", return_value=iter([test_db])
    ):
        texts = [
            "This is the first test document.",
            "This is the second test document.",
        ]
        geoparser.add_documents(texts)

    # Create a new mock for the get_documents call
    with patch(
        "geoparser.geoparserv2.geoparserv2.get_db", return_value=iter([test_db])
    ):
        # Retrieve all documents
        documents = geoparser.get_documents()

        # Verify we got the expected documents
        assert len(documents) == 2
        assert documents[0].text == texts[0]
        assert documents[1].text == texts[1]
        assert all(doc.project_id == geoparser.project_id for doc in documents)


def test_get_documents_by_id(test_db, geoparser_with_existing_project):
    """Test retrieving specific documents by ID."""
    geoparser = geoparser_with_existing_project

    # Add documents with one mock
    with patch(
        "geoparser.geoparserv2.geoparserv2.get_db", return_value=iter([test_db])
    ):
        texts = [
            "This is the first test document.",
            "This is the second test document.",
            "This is the third test document.",
        ]
        document_ids = geoparser.add_documents(texts)

    # Create a new mock for the get_documents call
    with patch(
        "geoparser.geoparserv2.geoparserv2.get_db", return_value=iter([test_db])
    ):
        # Retrieve only specific documents by IDs
        selected_ids = [document_ids[0], document_ids[2]]  # First and third documents
        documents = geoparser.get_documents(selected_ids)

        # Verify we got only the requested documents
        assert len(documents) == 2
        assert documents[0].id == document_ids[0]
        assert documents[0].text == texts[0]
        assert documents[1].id == document_ids[2]
        assert documents[1].text == texts[2]


def test_get_documents_empty_project(test_db, geoparser_with_existing_project):
    """Test retrieving documents for an empty project."""
    geoparser = geoparser_with_existing_project

    # Patch the get_db function with a fresh iterator
    with patch(
        "geoparser.geoparserv2.geoparserv2.get_db", return_value=iter([test_db])
    ):
        # Retrieve documents from empty project
        documents = geoparser.get_documents()

        # Verify we got an empty list
        assert len(documents) == 0
        assert documents == []


def test_run_module(geoparser_with_existing_project):
    """Test running a single module."""
    geoparser = geoparser_with_existing_project

    # Create a mock module
    mock_module = MagicMock(spec=BaseModule)

    # Patch the module_runner.run_module method
    with patch.object(geoparser.module_runner, "run_module") as mock_run:
        # Run the module
        geoparser.run_module(mock_module)

        # Verify module_runner.run_module was called correctly
        mock_run.assert_called_once_with(mock_module, geoparser.project_id)


def test_run_pipeline(geoparser_with_existing_project):
    """Test running the entire pipeline."""
    geoparser = geoparser_with_existing_project

    # Create mock modules for the pipeline
    mock_module1 = MagicMock(spec=BaseModule)
    mock_module2 = MagicMock(spec=BaseModule)
    mock_module3 = MagicMock(spec=BaseModule)

    # Add modules to the pipeline
    geoparser.pipeline = [mock_module1, mock_module2, mock_module3]

    # Patch the run_module method
    with patch.object(geoparser, "run_module") as mock_run:
        # Run the pipeline
        geoparser.run_pipeline()

        # Verify run_module was called for each module in the pipeline
        assert mock_run.call_count == 3
        mock_run.assert_any_call(mock_module1)
        mock_run.assert_any_call(mock_module2)
        mock_run.assert_any_call(mock_module3)


def test_parse_with_no_modules(test_db, geoparser_with_existing_project):
    """Test parsing with no modules configured."""
    geoparser = geoparser_with_existing_project

    # Patch the add_documents and get_documents methods
    with patch.object(geoparser, "add_documents") as mock_add:
        with patch.object(geoparser, "get_documents") as mock_get:
            with patch.object(geoparser, "run_pipeline") as mock_run_pipeline:
                # Set up mocks
                document_ids = [uuid.uuid4(), uuid.uuid4()]
                mock_documents = [MagicMock(), MagicMock()]
                mock_add.return_value = document_ids
                mock_get.return_value = mock_documents

                # Call parse
                text = "This is a test document."
                result = geoparser.parse(text)

                # Verify
                mock_add.assert_called_once_with(text)
                mock_run_pipeline.assert_called_once()
                mock_get.assert_called_once_with(document_ids)
                assert result == mock_documents


def test_parse_with_pipeline(test_db, geoparser_with_existing_project):
    """Test parsing with modules in the pipeline."""
    # Create mock modules
    mock_module1 = MagicMock(spec=BaseModule)
    mock_module2 = MagicMock(spec=BaseModule)

    # Set up the geoparser with pipeline
    geoparser = geoparser_with_existing_project
    geoparser.pipeline = [mock_module1, mock_module2]

    # Patch methods
    with patch.object(geoparser, "add_documents") as mock_add:
        with patch.object(geoparser, "get_documents") as mock_get:
            with patch.object(geoparser, "run_pipeline") as mock_run_pipeline:
                # Set up mocks
                document_ids = [uuid.uuid4()]
                mock_documents = [MagicMock()]
                mock_add.return_value = document_ids
                mock_get.return_value = mock_documents

                # Call parse
                text = "This is a test document."
                result = geoparser.parse(text)

                # Verify
                mock_add.assert_called_once_with(text)
                mock_run_pipeline.assert_called_once()
                mock_get.assert_called_once_with(document_ids)
                assert result == mock_documents
