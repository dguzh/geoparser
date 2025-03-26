import uuid
from unittest.mock import patch

from sqlmodel import Session

from geoparser.db.crud import DocumentRepository, ProjectRepository
from geoparser.db.models import Document, Project
from geoparser.geoparserv2.project import GeoparserProject


def test_load_project_existing(test_db: Session, test_project: Project):
    """Test loading an existing project."""
    geoparserproject = GeoparserProject.__new__(
        GeoparserProject
    )  # Create instance without calling __init__

    # Call load_project directly
    project = geoparserproject.load_project(test_db, test_project.name)

    assert project is not None
    assert project.id == test_project.id
    assert project.name == test_project.name


def test_load_project_nonexistent(test_db: Session):
    """Test loading a non-existent project."""
    geoparserproject = GeoparserProject.__new__(
        GeoparserProject
    )  # Create instance without calling __init__

    # Call load_project directly with a non-existent project name
    project = geoparserproject.load_project(test_db, "non-existent-project")

    assert project is None


def test_create_project(test_db: Session):
    """Test creating a new project."""
    geoparserproject = GeoparserProject.__new__(
        GeoparserProject
    )  # Create instance without calling __init__

    # Call create_project directly
    project_name = "new-test-project"
    project = geoparserproject.create_project(test_db, project_name)

    assert project is not None
    assert project.name == project_name

    # Verify it was saved to the database
    db_project = ProjectRepository.get_by_name(test_db, project_name)
    assert db_project is not None
    assert db_project.name == project_name


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


def test_initialize_project_existing(mock_get_db, test_db, test_project):
    """Test _initialize_project with an existing project."""
    geoparserproject = GeoparserProject.__new__(
        GeoparserProject
    )  # Create instance without calling __init__

    # Mock the load_project and create_project methods
    with patch.object(
        geoparserproject, "load_project", return_value=test_project
    ) as mock_load:
        with patch.object(geoparserproject, "create_project") as mock_create:
            project_id = geoparserproject._initialize_project(test_project.name)

            # Verify load_project was called with the correct arguments
            mock_load.assert_called_once_with(test_db, test_project.name)

            # Verify create_project was not called
            mock_create.assert_not_called()

            # Verify the correct project id was returned
            assert project_id == test_project.id


def test_initialize_project_new(mock_get_db, test_db):
    """Test _initialize_project with a new project."""
    geoparserproject = GeoparserProject.__new__(
        GeoparserProject
    )  # Create instance without calling __init__

    new_project = Project(name="new-project", id=uuid.uuid4())

    # Mock the load_project and create_project methods
    with patch.object(geoparserproject, "load_project", return_value=None) as mock_load:
        with patch.object(
            geoparserproject, "create_project", return_value=new_project
        ) as mock_create:
            with patch("geoparser.geoparserv2.project.logging.info") as mock_log:
                project_id = geoparserproject._initialize_project("new-project")

                # Verify load_project was called with the correct arguments
                mock_load.assert_called_once_with(test_db, "new-project")

                # Verify create_project was called with the correct arguments
                mock_create.assert_called_once_with(test_db, "new-project")

                # Verify logging was called
                mock_log.assert_called_once()
                assert (
                    "No project found with name 'new-project'"
                    in mock_log.call_args[0][0]
                )

                # Verify the correct project id was returned
                assert project_id == new_project.id


def test_add_documents_single(test_db, geoparserproject_with_existing_project):
    """Test adding a single document."""
    geoparserproject = geoparserproject_with_existing_project

    # Patch the get_db function to return a fresh iterator each time
    with patch("geoparser.geoparserv2.project.get_db", return_value=iter([test_db])):
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
    with patch("geoparser.geoparserv2.project.get_db", return_value=iter([test_db])):
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
    with patch("geoparser.geoparserv2.project.get_db", return_value=iter([test_db])):
        texts = [
            "This is the first test document.",
            "This is the second test document.",
        ]
        geoparserproject.add_documents(texts)

    # Create a new mock for the get_documents call
    with patch("geoparser.geoparserv2.project.get_db", return_value=iter([test_db])):
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
    with patch("geoparser.geoparserv2.project.get_db", return_value=iter([test_db])):
        texts = [
            "This is the first test document.",
            "This is the second test document.",
            "This is the third test document.",
        ]
        document_ids = geoparserproject.add_documents(texts)

    # Create a new mock for the get_documents call
    with patch("geoparser.geoparserv2.project.get_db", return_value=iter([test_db])):
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
    with patch("geoparser.geoparserv2.project.get_db", return_value=iter([test_db])):
        # Retrieve documents from empty project
        documents = geoparserproject.get_documents()

        # Verify we got an empty list
        assert len(documents) == 0
        assert documents == []
