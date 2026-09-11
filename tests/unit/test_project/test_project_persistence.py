"""
Tests for Project against a real (in-memory) database.

The rest of the Project tests mock the repositories, which is fast but blind
to whether the session actually reaches them: a repository call that is handed
``None`` instead of the open session looks identical to a correct one under a
Mock, and only fails when there is a database on the other end. These run the
same operations for real, so the wiring is checked as well as the arguments.
"""

import uuid
from unittest.mock import patch

import pytest

from geoparser.project.project import Project


@pytest.fixture
def project() -> Project:
    """A project backed by the in-memory test database."""
    return Project("persistence")


@pytest.mark.unit
class TestProjectRecord:
    """Creating and reusing the project's own row."""

    def test_creates_a_record_and_reuses_it_by_name(self, project):
        """Opening the same name twice yields the same project id."""
        # Act
        reopened = Project("persistence")

        # Assert
        assert reopened.id == project.id

    def test_distinct_names_get_distinct_records(self, project):
        """A different name is a different project."""
        # Act
        other = Project("something-else")

        # Assert
        assert other.id != project.id

    def test_the_context_is_scoped_to_this_project(self, project):
        """The context reads and writes rows for this project only."""
        # Assert
        assert project.context.project_id == project.id


@pytest.mark.unit
class TestDocumentRoundTrip:
    """Writing documents and reading them back."""

    def test_created_documents_are_readable_in_order(self, project):
        """Texts go in, documents come back in the same order."""
        # Act
        ids = project.create_documents(["first", "second", "third"])
        documents = project.get_documents()

        # Assert
        assert len(ids) == 3
        assert [document.text for document in documents] == [
            "first",
            "second",
            "third",
        ]

    def test_documents_belong_to_the_project_that_created_them(self, project):
        """Another project does not see these documents."""
        # Arrange
        project.create_documents(["mine"])
        other = Project("other")

        # Act & Assert
        assert other.get_documents() == []

    def test_requested_ids_come_back_in_the_order_asked_for(self, project):
        """Retrieval order follows the request, not the insertion order."""
        # Arrange
        first, second, third = project.create_documents(["a", "b", "c"])

        # Act
        documents = project.get_documents([third, first, second])

        # Assert
        assert [document.text for document in documents] == ["c", "a", "b"]

    def test_an_unknown_id_is_reported_by_value(self, project):
        """The error names the id that was not found."""
        # Arrange
        project.create_documents(["a"])
        unknown = uuid.uuid4()

        # Act & Assert
        with pytest.raises(ValueError, match=str(unknown)):
            project.get_documents([unknown])

    def test_several_unknown_ids_are_listed_comma_separated(self, project):
        """Every missing id is listed, so a caller can fix them in one go."""
        # Arrange
        first, second = uuid.uuid4(), uuid.uuid4()

        # Act & Assert
        with pytest.raises(ValueError, match=f"{first}, {second}"):
            project.get_documents([first, second])


@pytest.mark.unit
class TestDelete:
    """Removing a project."""

    def test_delete_removes_the_project_and_its_documents(self, project):
        """After deleting, reopening the name starts from an empty project."""
        # Arrange
        project.create_documents(["a", "b"])

        # Act
        project.delete()
        reopened = Project("persistence")

        # Assert
        assert reopened.id != project.id
        assert reopened.get_documents() == []


@pytest.mark.unit
class TestManualAnnotationTags:
    """The tag manual annotations are filed under."""

    def test_create_references_files_them_under_the_given_tag(self, project):
        """The tag reaches run_recognizer rather than falling back to latest."""
        # Arrange & Act
        with patch.object(project, "run_recognizer") as run:
            project.create_references(["Paris"], [[(0, 5)]], tag="gold")

        # Assert
        assert run.call_args.kwargs["tag"] == "gold"

    def test_create_referents_files_them_under_the_given_tag(self, project):
        """The tag reaches run_resolver rather than falling back to latest."""
        # Arrange & Act
        with patch.object(project, "run_resolver") as run:
            project.create_referents(
                ["Paris"], [[(0, 5)]], [[("geonames", "1")]], tag="gold"
            )

        # Assert
        assert run.call_args.kwargs["tag"] == "gold"
