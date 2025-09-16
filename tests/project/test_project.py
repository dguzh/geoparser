import uuid
from unittest.mock import patch

from geoparser.db.crud import DocumentRepository, ProjectRepository
from geoparser.project.project import Project


def test_project_initialization_new_project(test_db):
    """Test Project initialization with a new project name."""
    project_name = "new-test-project"

    with patch("geoparser.project.project.Session") as mock_session:
        mock_session.return_value.__enter__.return_value = test_db
        mock_session.return_value.__exit__.return_value = None

        project = Project(project_name)

        assert project.project_name == project_name
        assert project.id is not None

        # Verify project was created in database
        db_project = ProjectRepository.get_by_name(test_db, project_name)
        assert db_project is not None
        assert db_project.name == project_name
        assert db_project.id == project.id


def test_project_initialization_existing_project(test_db, test_project_model):
    """Test Project initialization with an existing project name."""
    with patch("geoparser.project.project.Session") as mock_session:
        mock_session.return_value.__enter__.return_value = test_db
        mock_session.return_value.__exit__.return_value = None

        project = Project(test_project_model.name)

        assert project.project_name == test_project_model.name
        assert project.id == test_project_model.id


def test_add_documents_single_string(test_db):
    """Test adding a single document as a string."""
    project_name = "test-project"
    text = "This is a test document."

    with patch("geoparser.project.project.Session") as mock_session:
        mock_session.return_value.__enter__.return_value = test_db
        mock_session.return_value.__exit__.return_value = None

        project = Project(project_name)
        project.add_documents(text)

        # Verify document was added
        documents = DocumentRepository.get_by_project(test_db, project.id)
        assert len(documents) == 1
        assert documents[0].text == text
        assert documents[0].project_id == project.id


def test_add_documents_multiple_strings(test_db):
    """Test adding multiple documents as a list of strings."""
    project_name = "test-project"
    texts = [
        "This is the first document.",
        "This is the second document.",
        "This is the third document.",
    ]

    with patch("geoparser.project.project.Session") as mock_session:
        mock_session.return_value.__enter__.return_value = test_db
        mock_session.return_value.__exit__.return_value = None

        project = Project(project_name)
        project.add_documents(texts)

        # Verify documents were added
        documents = DocumentRepository.get_by_project(test_db, project.id)
        assert len(documents) == 3
        for i, doc in enumerate(documents):
            assert doc.text == texts[i]
            assert doc.project_id == project.id


def test_get_documents_no_filters(test_db):
    """Test getting documents without any filters."""
    project_name = "test-project"
    texts = ["Document 1", "Document 2"]

    with patch("geoparser.project.project.Session") as mock_session:
        mock_session.return_value.__enter__.return_value = test_db
        mock_session.return_value.__exit__.return_value = None

        project = Project(project_name)
        project.add_documents(texts)

        # Get documents without filters
        documents = project.get_documents()

        assert len(documents) == 2
        for doc in documents:
            assert doc.references == []  # No references without recognizer_id


def test_get_documents_with_recognizer_filter(test_db):
    """Test getting documents with recognizer filter."""
    project_name = "test-project"
    recognizer_id = uuid.uuid4()

    with patch("geoparser.project.project.Session") as mock_session:
        mock_session.return_value.__enter__.return_value = test_db
        mock_session.return_value.__exit__.return_value = None

        project = Project(project_name)
        project.add_documents("Test document")

        # Get documents with recognizer filter
        documents = project.get_documents(recognizer_id=recognizer_id)

        assert len(documents) == 1
        # References should be empty since no references exist for this recognizer
        assert documents[0].references == []


def test_get_documents_with_resolver_filter(test_db):
    """Test getting documents with resolver filter."""
    project_name = "test-project"
    recognizer_id = uuid.uuid4()
    resolver_id = uuid.uuid4()

    with patch("geoparser.project.project.Session") as mock_session:
        mock_session.return_value.__enter__.return_value = test_db
        mock_session.return_value.__exit__.return_value = None

        project = Project(project_name)
        project.add_documents("Test document")

        # Get documents with both recognizer and resolver filters
        documents = project.get_documents(
            recognizer_id=recognizer_id, resolver_id=resolver_id
        )

        assert len(documents) == 1
        # References should be empty since no references exist
        assert documents[0].references == []


def test_delete_project(test_db):
    """Test deleting a project."""
    project_name = "test-project-to-delete"

    with patch("geoparser.project.project.Session") as mock_session:
        mock_session.return_value.__enter__.return_value = test_db
        mock_session.return_value.__exit__.return_value = None

        project = Project(project_name)
        project_id = project.id

        # Add some documents
        project.add_documents(["Document 1", "Document 2"])

        # Verify project exists
        db_project = ProjectRepository.get_by_name(test_db, project_name)
        assert db_project is not None

        # Delete the project
        project.delete()

        # Verify project was deleted
        db_project = test_db.get(type(db_project), project_id)
        assert db_project is None


def test_get_documents_empty_project(test_db):
    """Test getting documents from an empty project."""
    project_name = "empty-project"

    with patch("geoparser.project.project.Session") as mock_session:
        mock_session.return_value.__enter__.return_value = test_db
        mock_session.return_value.__exit__.return_value = None

        project = Project(project_name)

        # Get documents from empty project
        documents = project.get_documents()

        assert len(documents) == 0
        assert documents == []
