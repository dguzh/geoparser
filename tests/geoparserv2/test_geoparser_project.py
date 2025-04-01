import uuid
from unittest.mock import patch

from sqlmodel import Session

from geoparser.db.crud import DocumentRepository, ProjectRepository
from geoparser.db.models import Document, Project
from geoparser.geoparserv2.geoparser_project import GeoparserProject


def test_initialize_project_existing(test_db: Session, test_project: Project):
    """Test _initialize_project with an existing project."""
    geoparserproject = GeoparserProject.__new__(
        GeoparserProject
    )  # Create instance without calling __init__

    # Mock ProjectRepository.get_by_name to return the test project
    with patch(
        "geoparser.geoparserv2.geoparser_project.ProjectRepository.get_by_name",
        return_value=test_project,
    ):
        with patch(
            "geoparser.geoparserv2.geoparser_project.get_db",
            return_value=iter([test_db]),
        ):
            project_id = geoparserproject._initialize_project(test_project.name)

            # Verify the correct project id was returned
            assert project_id == test_project.id


def test_initialize_project_new(test_db: Session):
    """Test _initialize_project with a new project."""
    geoparserproject = GeoparserProject.__new__(
        GeoparserProject
    )  # Create instance without calling __init__

    # Mock ProjectRepository.get_by_name to return None (project doesn't exist)
    with patch(
        "geoparser.geoparserv2.geoparser_project.ProjectRepository.get_by_name",
        return_value=None,
    ):
        # Mock ProjectRepository.create to return a new project
        new_project = Project(name="new-project", id=uuid.uuid4())
        with patch(
            "geoparser.geoparserv2.geoparser_project.ProjectRepository.create",
            return_value=new_project,
        ):
            with patch(
                "geoparser.geoparserv2.geoparser_project.get_db",
                return_value=iter([test_db]),
            ):
                with patch(
                    "geoparser.geoparserv2.geoparser_project.logging.info"
                ) as mock_log:
                    project_id = geoparserproject._initialize_project("new-project")

                    # Verify logging was called
                    mock_log.assert_called_once()
                    assert (
                        "No project found with name 'new-project'"
                        in mock_log.call_args[0][0]
                    )

                    # Verify the correct project id was returned
                    assert project_id == new_project.id


def test_init_with_existing_project(
    geoparserproject_with_existing_project, test_project
):
    """Test initializing GeoparserProject with an existing project."""
    geoparserproject = geoparserproject_with_existing_project

    assert geoparserproject.project_id is not None
    assert geoparserproject.project_id == test_project.id
    assert geoparserproject.project_name == test_project.name


def test_init_with_new_project(geoparserproject_with_new_project, test_db):
    """Test initializing GeoparserProject with a new project name."""
    geoparserproject = geoparserproject_with_new_project

    assert geoparserproject.project_id is not None
    assert geoparserproject.project_name == "new-test-project"

    # Verify it was saved to the database
    db_project = ProjectRepository.get_by_name(test_db, "new-test-project")
    assert db_project is not None
    assert db_project.name == "new-test-project"


def test_init_with_no_project_name(test_db):
    """Test initializing GeoparserProject without providing a project name."""
    # Mock get_db to return the test database
    with patch(
        "geoparser.geoparserv2.geoparser_project.get_db", return_value=iter([test_db])
    ):
        with patch(
            "uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")
        ):
            geoparserproject = GeoparserProject()

            # Verify that a temporary project name was generated
            assert geoparserproject.project_name.startswith("temp_project_")
            assert (
                "12345678-1234-5678-1234-567812345678" in geoparserproject.project_name
            )

            # Verify that a project was created in the database
            db_project = ProjectRepository.get_by_name(
                test_db, geoparserproject.project_name
            )
            assert db_project is not None
            assert db_project.name == geoparserproject.project_name


def test_add_documents_single(test_db, geoparserproject_with_existing_project):
    """Test adding a single document."""
    geoparserproject = geoparserproject_with_existing_project

    # Patch the get_db function to return a fresh iterator each time
    with patch(
        "geoparser.geoparserv2.geoparser_project.get_db", return_value=iter([test_db])
    ):
        # Add a single document
        document_ids = geoparserproject.add_documents("This is a test document.")

        # Verify the document was created
        assert len(document_ids) == 1

        # Verify it was saved to the database
        document = test_db.get(Document, document_ids[0])
        assert document is not None
        assert document.text == "This is a test document."
        assert document.project_id == geoparserproject.project_id


def test_add_documents_multiple(test_db, geoparserproject_with_existing_project):
    """Test adding multiple documents."""
    geoparserproject = geoparserproject_with_existing_project

    # Patch the get_db function to return a fresh iterator each time
    with patch(
        "geoparser.geoparserv2.geoparser_project.get_db", return_value=iter([test_db])
    ):
        # Add multiple documents
        texts = [
            "This is the first test document.",
            "This is the second test document.",
            "This is the third test document.",
        ]
        document_ids = geoparserproject.add_documents(texts)

        # Verify the documents were created
        assert len(document_ids) == 3

        # Verify they were saved to the database
        for i, doc_id in enumerate(document_ids):
            document = test_db.get(Document, doc_id)
            assert document is not None
            assert document.text == texts[i]
            assert document.project_id == geoparserproject.project_id

        # Verify we can retrieve all documents for the project
        documents = DocumentRepository.get_by_project(
            test_db, geoparserproject.project_id
        )
        assert len(documents) == 3


def test_get_documents_all(test_db, geoparserproject_with_existing_project):
    """Test retrieving all documents for a project."""
    geoparserproject = geoparserproject_with_existing_project

    # Add multiple documents with one mock
    with patch(
        "geoparser.geoparserv2.geoparser_project.get_db", return_value=iter([test_db])
    ):
        texts = [
            "This is the first test document.",
            "This is the second test document.",
        ]
        geoparserproject.add_documents(texts)

    # Create a new mock for the get_documents call
    with patch(
        "geoparser.geoparserv2.geoparser_project.get_db", return_value=iter([test_db])
    ):
        # Retrieve all documents
        documents = geoparserproject.get_documents()

        # Verify we got the expected documents
        assert len(documents) == 2
        assert documents[0].text == texts[0]
        assert documents[1].text == texts[1]
        assert all(doc.project_id == geoparserproject.project_id for doc in documents)


def test_get_documents_by_id(test_db, geoparserproject_with_existing_project):
    """Test retrieving specific documents by ID."""
    geoparserproject = geoparserproject_with_existing_project

    # Add documents with one mock
    with patch(
        "geoparser.geoparserv2.geoparser_project.get_db", return_value=iter([test_db])
    ):
        texts = [
            "This is the first test document.",
            "This is the second test document.",
            "This is the third test document.",
        ]
        document_ids = geoparserproject.add_documents(texts)

    # Create a new mock for the get_documents call
    with patch(
        "geoparser.geoparserv2.geoparser_project.get_db", return_value=iter([test_db])
    ):
        # Retrieve only specific documents by IDs
        selected_ids = [document_ids[0], document_ids[2]]  # First and third documents
        documents = geoparserproject.get_documents(selected_ids)

        # Verify we got only the requested documents
        assert len(documents) == 2
        assert documents[0].id == document_ids[0]
        assert documents[0].text == texts[0]
        assert documents[1].id == document_ids[2]
        assert documents[1].text == texts[2]


def test_get_documents_empty_project(test_db, geoparserproject_with_existing_project):
    """Test retrieving documents for an empty project."""
    geoparserproject = geoparserproject_with_existing_project

    # Patch the get_db function with a fresh iterator
    with patch(
        "geoparser.geoparserv2.geoparser_project.get_db", return_value=iter([test_db])
    ):
        # Retrieve documents from empty project
        documents = geoparserproject.get_documents()

        # Verify we got an empty list
        assert len(documents) == 0
        assert documents == []
