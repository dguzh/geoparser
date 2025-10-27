"""
Unit tests for geoparser/project/project.py

Tests the Project class with mocked dependencies.
"""

from unittest.mock import ANY, Mock, patch
from uuid import UUID

import pytest

from geoparser.project.project import Project


@pytest.mark.unit
class TestProjectInitialization:
    """Test Project initialization."""

    @patch("geoparser.project.project.ProjectRepository")
    def test_creates_new_project_when_doesnt_exist(self, mock_project_repo):
        """Test that Project creates a new project record when it doesn't exist."""
        # Arrange
        mock_project_repo.get_by_name.return_value = None  # Project doesn't exist

        mock_created_project = Mock()
        mock_created_project.id = UUID("12345678-1234-5678-1234-567812345678")
        mock_project_repo.create.return_value = mock_created_project

        # Act
        project = Project("NewProject")

        # Assert
        assert project.name == "NewProject"
        assert project.id == UUID("12345678-1234-5678-1234-567812345678")
        mock_project_repo.create.assert_called_once()

    @patch("geoparser.project.project.ProjectRepository")
    def test_loads_existing_project_when_exists(self, mock_project_repo):
        """Test that Project loads existing project record when it exists."""
        # Arrange

        mock_existing_project = Mock()
        mock_existing_project.id = UUID("87654321-4321-8765-4321-876543218765")
        mock_project_repo.get_by_name.return_value = mock_existing_project

        # Act
        project = Project("ExistingProject")

        # Assert
        assert project.name == "ExistingProject"
        assert project.id == UUID("87654321-4321-8765-4321-876543218765")
        mock_project_repo.create.assert_not_called()


@pytest.mark.unit
class TestProjectCreateDocuments:
    """Test Project create_documents method."""

    @patch("geoparser.project.project.ProjectRepository")
    @patch("geoparser.project.project.DocumentRepository")
    def test_creates_single_document(self, mock_doc_repo, mock_project_repo):
        """Test that create_documents creates a single document from a string."""
        # Arrange

        mock_existing_project = Mock()
        mock_existing_project.id = UUID("12345678-1234-5678-1234-567812345678")
        mock_project_repo.get_by_name.return_value = mock_existing_project

        project = Project("TestProject")

        # Act
        project.create_documents("Test document text")

        # Assert
        mock_doc_repo.create.assert_called_once()
        call_args = mock_doc_repo.create.call_args[0]
        assert call_args[1].text == "Test document text"
        assert call_args[1].project_id == project.id

    @patch("geoparser.project.project.ProjectRepository")
    @patch("geoparser.project.project.DocumentRepository")
    def test_creates_multiple_documents(self, mock_doc_repo, mock_project_repo):
        """Test that create_documents creates multiple documents from a list."""
        # Arrange

        mock_existing_project = Mock()
        mock_existing_project.id = UUID("12345678-1234-5678-1234-567812345678")
        mock_project_repo.get_by_name.return_value = mock_existing_project

        project = Project("TestProject")

        # Act
        project.create_documents(["Doc 1", "Doc 2", "Doc 3"])

        # Assert
        assert mock_doc_repo.create.call_count == 3
        call_args_list = [
            call[0][1].text for call in mock_doc_repo.create.call_args_list
        ]
        assert "Doc 1" in call_args_list
        assert "Doc 2" in call_args_list
        assert "Doc 3" in call_args_list


@pytest.mark.unit
class TestProjectGetDocuments:
    """Test Project get_documents method."""

    @patch("geoparser.project.project.ProjectRepository")
    @patch("geoparser.project.project.DocumentRepository")
    def test_retrieves_documents_for_project(self, mock_doc_repo, mock_project_repo):
        """Test that get_documents retrieves all documents for the project."""
        # Arrange

        mock_existing_project = Mock()
        mock_existing_project.id = UUID("12345678-1234-5678-1234-567812345678")
        mock_project_repo.get_by_name.return_value = mock_existing_project

        mock_doc1 = Mock()
        mock_doc1.references = []
        mock_doc2 = Mock()
        mock_doc2.references = []
        mock_doc_repo.get_by_project.return_value = [mock_doc1, mock_doc2]

        project = Project("TestProject")

        # Act
        documents = project.get_documents()

        # Assert
        assert len(documents) == 2
        mock_doc_repo.get_by_project.assert_called_once_with(ANY, project.id)

    @patch("geoparser.project.project.ProjectRepository")
    @patch("geoparser.project.project.DocumentRepository")
    def test_sets_recognizer_context_on_documents(
        self, mock_doc_repo, mock_project_repo
    ):
        """Test that get_documents sets recognizer context on documents."""
        # Arrange

        mock_existing_project = Mock()
        mock_existing_project.id = UUID("12345678-1234-5678-1234-567812345678")
        mock_project_repo.get_by_name.return_value = mock_existing_project

        mock_doc = Mock()
        mock_doc.references = []
        mock_doc_repo.get_by_project.return_value = [mock_doc]

        project = Project("TestProject")

        # Act
        project.get_documents(recognizer_id="test_recognizer")

        # Assert
        mock_doc._set_recognizer_context.assert_called_once_with("test_recognizer")

    @patch("geoparser.project.project.ProjectRepository")
    @patch("geoparser.project.project.DocumentRepository")
    def test_sets_resolver_context_on_references(
        self, mock_doc_repo, mock_project_repo
    ):
        """Test that get_documents sets resolver context on references."""
        # Arrange

        mock_existing_project = Mock()
        mock_existing_project.id = UUID("12345678-1234-5678-1234-567812345678")
        mock_project_repo.get_by_name.return_value = mock_existing_project

        mock_ref1 = Mock()
        mock_ref2 = Mock()
        mock_doc = Mock()
        mock_doc.references = [mock_ref1, mock_ref2]
        mock_doc_repo.get_by_project.return_value = [mock_doc]

        project = Project("TestProject")

        # Act
        project.get_documents(resolver_id="test_resolver")

        # Assert
        mock_ref1._set_resolver_context.assert_called_once_with("test_resolver")
        mock_ref2._set_resolver_context.assert_called_once_with("test_resolver")


@pytest.mark.unit
class TestProjectRunRecognizer:
    """Test Project run_recognizer method."""

    @patch("geoparser.project.project.ProjectRepository")
    @patch("geoparser.project.project.RecognitionService")
    @patch("geoparser.project.project.DocumentRepository")
    def test_runs_recognizer_on_all_documents(
        self, mock_doc_repo, mock_recognition_service, mock_project_repo
    ):
        """Test that run_recognizer runs recognizer on all project documents."""
        # Arrange

        mock_existing_project = Mock()
        mock_existing_project.id = UUID("12345678-1234-5678-1234-567812345678")
        mock_project_repo.get_by_name.return_value = mock_existing_project

        mock_doc1 = Mock()
        mock_doc1.references = []
        mock_doc2 = Mock()
        mock_doc2.references = []
        mock_doc_repo.get_by_project.return_value = [mock_doc1, mock_doc2]

        mock_recognizer = Mock()
        mock_service_instance = Mock()
        mock_recognition_service.return_value = mock_service_instance

        project = Project("TestProject")

        # Act
        project.run_recognizer(mock_recognizer)

        # Assert
        mock_recognition_service.assert_called_once_with(mock_recognizer)
        mock_service_instance.predict.assert_called_once()
        called_docs = mock_service_instance.predict.call_args[0][0]
        assert len(called_docs) == 2


@pytest.mark.unit
class TestProjectRunResolver:
    """Test Project run_resolver method."""

    @patch("geoparser.project.project.ProjectRepository")
    @patch("geoparser.project.project.ResolutionService")
    @patch("geoparser.project.project.DocumentRepository")
    def test_runs_resolver_on_all_documents(
        self, mock_doc_repo, mock_resolution_service, mock_project_repo
    ):
        """Test that run_resolver runs resolver on all project documents."""
        # Arrange

        mock_existing_project = Mock()
        mock_existing_project.id = UUID("12345678-1234-5678-1234-567812345678")
        mock_project_repo.get_by_name.return_value = mock_existing_project

        mock_doc1 = Mock()
        mock_doc1.references = []
        mock_doc2 = Mock()
        mock_doc2.references = []
        mock_doc_repo.get_by_project.return_value = [mock_doc1, mock_doc2]

        mock_resolver = Mock()
        mock_service_instance = Mock()
        mock_resolution_service.return_value = mock_service_instance

        project = Project("TestProject")

        # Act
        project.run_resolver(mock_resolver)

        # Assert
        mock_resolution_service.assert_called_once_with(mock_resolver)
        mock_service_instance.predict.assert_called_once()
        called_docs = mock_service_instance.predict.call_args[0][0]
        assert len(called_docs) == 2


@pytest.mark.unit
class TestProjectDelete:
    """Test Project delete method."""

    @patch("geoparser.project.project.ProjectRepository")
    def test_deletes_project_from_database(self, mock_project_repo):
        """Test that delete removes the project from the database."""
        # Arrange

        mock_existing_project = Mock()
        mock_existing_project.id = UUID("12345678-1234-5678-1234-567812345678")
        mock_project_repo.get_by_name.return_value = mock_existing_project

        project = Project("TestProject")

        # Act
        project.delete()

        # Assert
        mock_project_repo.delete.assert_called_once_with(ANY, id=project.id)


@pytest.mark.unit
class TestProjectCreateReferences:
    """Test Project create_references method."""

    @patch("geoparser.project.project.ProjectRepository")
    @patch("geoparser.project.project.ManualRecognizer")
    @patch("geoparser.project.project.RecognitionService")
    @patch("geoparser.project.project.DocumentRepository")
    def test_creates_manual_recognizer_and_runs_it(
        self,
        mock_doc_repo,
        mock_recognition_service,
        mock_manual_recognizer,
        mock_project_repo,
    ):
        """Test that create_references creates ManualRecognizer and runs it."""
        # Arrange

        mock_existing_project = Mock()
        mock_existing_project.id = UUID("12345678-1234-5678-1234-567812345678")
        mock_project_repo.get_by_name.return_value = mock_existing_project

        mock_doc = Mock()
        mock_doc.references = []
        mock_doc_repo.get_by_project.return_value = [mock_doc]

        mock_recognizer_instance = Mock()
        mock_manual_recognizer.return_value = mock_recognizer_instance

        mock_service_instance = Mock()
        mock_recognition_service.return_value = mock_service_instance

        project = Project("TestProject")

        texts = ["Doc 1"]
        references = [[(0, 5)]]

        # Act
        project.create_references(texts, references, "test_label")

        # Assert
        mock_manual_recognizer.assert_called_once_with(
            label="test_label", texts=texts, references=references
        )
        mock_recognition_service.assert_called_once_with(mock_recognizer_instance)
        mock_service_instance.predict.assert_called_once()


@pytest.mark.unit
class TestProjectCreateReferents:
    """Test Project create_referents method."""

    @patch("geoparser.project.project.ProjectRepository")
    @patch("geoparser.project.project.ManualResolver")
    @patch("geoparser.project.project.ResolutionService")
    @patch("geoparser.project.project.DocumentRepository")
    def test_creates_manual_resolver_and_runs_it(
        self,
        mock_doc_repo,
        mock_resolution_service,
        mock_manual_resolver,
        mock_project_repo,
    ):
        """Test that create_referents creates ManualResolver and runs it."""
        # Arrange

        mock_existing_project = Mock()
        mock_existing_project.id = UUID("12345678-1234-5678-1234-567812345678")
        mock_project_repo.get_by_name.return_value = mock_existing_project

        mock_doc = Mock()
        mock_doc.references = []
        mock_doc_repo.get_by_project.return_value = [mock_doc]

        mock_resolver_instance = Mock()
        mock_manual_resolver.return_value = mock_resolver_instance

        mock_service_instance = Mock()
        mock_resolution_service.return_value = mock_service_instance

        project = Project("TestProject")

        texts = ["Doc 1"]
        references = [[(0, 5)]]
        referents = [[("geonames", "123")]]

        # Act
        project.create_referents(texts, references, referents, "test_label")

        # Assert
        mock_manual_resolver.assert_called_once_with(
            label="test_label",
            texts=texts,
            references=references,
            referents=referents,
        )
        mock_resolution_service.assert_called_once_with(mock_resolver_instance)
        mock_service_instance.predict.assert_called_once()


@pytest.mark.unit
class TestProjectLoadAnnotations:
    """Test Project load_annotations method."""

    @patch("geoparser.project.project.ProjectRepository")
    @patch("geoparser.project.project.open", create=True)
    def test_loads_annotations_from_json_file(self, mock_file_open, mock_project_repo):
        """Test that load_annotations loads and parses JSON file."""
        # Arrange

        mock_existing_project = Mock()
        mock_existing_project.id = UUID("12345678-1234-5678-1234-567812345678")
        mock_project_repo.get_by_name.return_value = mock_existing_project

        json_data = {
            "gazetteer": "geonames",
            "documents": [
                {
                    "text": "Paris is beautiful",
                    "toponyms": [
                        {"start": 0, "end": 5, "loc_id": "123"},
                        {"start": 10, "end": 19, "loc_id": ""},  # Not geocoded
                    ],
                }
            ],
        }

        mock_file_open.return_value.__enter__.return_value.read.return_value = str(
            json_data
        )

        # Mock json.load
        with patch("geoparser.project.project.json.load", return_value=json_data):
            with patch.object(Project, "create_references"):
                with patch.object(Project, "create_referents"):
                    project = Project("TestProject")

                    # Act
                    project.load_annotations("test.json")

                    # Assert - Verify file was opened
                    mock_file_open.assert_called_once()

    @patch("geoparser.project.project.ProjectRepository")
    @patch("geoparser.project.project.open", create=True)
    def test_creates_documents_when_requested(self, mock_file_open, mock_project_repo):
        """Test that load_annotations creates documents when create_documents=True."""
        # Arrange

        mock_existing_project = Mock()
        mock_existing_project.id = UUID("12345678-1234-5678-1234-567812345678")
        mock_project_repo.get_by_name.return_value = mock_existing_project

        json_data = {
            "gazetteer": "geonames",
            "documents": [{"text": "Paris", "toponyms": []}],
        }

        with patch("geoparser.project.project.json.load", return_value=json_data):
            with patch.object(Project, "create_documents") as mock_create_docs:
                with patch.object(Project, "create_references"):
                    with patch.object(Project, "create_referents"):
                        project = Project("TestProject")

                        # Act
                        project.load_annotations("test.json", create_documents=True)

                        # Assert
                        mock_create_docs.assert_called_once_with(["Paris"])

    @patch("geoparser.project.project.ProjectRepository")
    @patch("geoparser.project.project.open", create=True)
    def test_skips_document_creation_by_default(
        self, mock_file_open, mock_project_repo
    ):
        """Test that load_annotations doesn't create documents by default."""
        # Arrange

        mock_existing_project = Mock()
        mock_existing_project.id = UUID("12345678-1234-5678-1234-567812345678")
        mock_project_repo.get_by_name.return_value = mock_existing_project

        json_data = {
            "gazetteer": "geonames",
            "documents": [{"text": "Paris", "toponyms": []}],
        }

        with patch("geoparser.project.project.json.load", return_value=json_data):
            with patch.object(Project, "create_documents") as mock_create_docs:
                with patch.object(Project, "create_references"):
                    with patch.object(Project, "create_referents"):
                        project = Project("TestProject")

                        # Act
                        project.load_annotations("test.json")

                        # Assert
                        mock_create_docs.assert_not_called()

    @patch("geoparser.project.project.ProjectRepository")
    @patch("geoparser.project.project.open", create=True)
    def test_filters_out_non_geocoded_referents(
        self, mock_file_open, mock_project_repo
    ):
        """Test that load_annotations filters out non-geocoded referents (empty or null loc_id)."""
        # Arrange

        mock_existing_project = Mock()
        mock_existing_project.id = UUID("12345678-1234-5678-1234-567812345678")
        mock_project_repo.get_by_name.return_value = mock_existing_project

        json_data = {
            "gazetteer": "geonames",
            "documents": [
                {
                    "text": "Paris and London",
                    "toponyms": [
                        {"start": 0, "end": 5, "loc_id": "123"},  # Geocoded
                        {"start": 10, "end": 16, "loc_id": ""},  # Not geocoded (empty)
                    ],
                }
            ],
        }

        with patch("geoparser.project.project.json.load", return_value=json_data):
            with patch.object(Project, "create_references"):
                with patch.object(Project, "create_referents") as mock_create_ref:
                    project = Project("TestProject")

                    # Act
                    project.load_annotations("test.json")

                    # Assert
                    # Should create referents with None for non-geocoded
                    call_args = mock_create_ref.call_args[0]
                    referents = call_args[2]  # Third argument is referents
                    assert referents == [[("geonames", "123"), None]]
