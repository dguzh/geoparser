"""
Tests for how Project moves identifiers and texts into the database.

These pin the arguments rather than the call counts: passing the session and
the name in the wrong order, or dropping the project id from a document, still
looks like a successful call while writing the wrong rows.
"""

import uuid
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from geoparser.project.project import Project


@pytest.mark.unit
class TestNormalizeDocumentIds:
    """Accepting IDs as UUIDs, strings, or sequences of either."""

    def test_wraps_a_single_uuid(self):
        """One UUID becomes a one-element list."""
        # Arrange
        one = uuid.uuid4()

        # Act & Assert
        assert Project._normalize_document_ids(one) == [one]

    def test_wraps_and_parses_a_single_string(self):
        """One string ID is parsed into a UUID."""
        # Arrange
        one = uuid.uuid4()

        # Act & Assert
        assert Project._normalize_document_ids(str(one)) == [one]

    def test_keeps_the_order_of_a_sequence(self):
        """A sequence comes back in the order it was given."""
        # Arrange
        first, second = uuid.uuid4(), uuid.uuid4()

        # Act
        normalized = Project._normalize_document_ids([str(second), first])

        # Assert
        assert normalized == [second, first]

    def test_rejects_a_value_that_is_not_an_id(self):
        """Anything unparseable is reported rather than silently skipped."""
        # Act & Assert
        with pytest.raises(ValueError):
            Project._normalize_document_ids(["not-a-uuid"])


@pytest.mark.unit
class TestCreateDocuments:
    """Turning texts into document rows."""

    @staticmethod
    def _project() -> Project:
        """A Project with its database interactions stubbed out."""
        project = Project.__new__(Project)
        project.name = "demo"
        project.id = uuid.uuid4()
        return project

    def test_rejects_a_bare_string(self):
        """
        A single string would be iterated character by character.

        The guard exists so that create_documents("hello") does not silently
        create five documents.
        """
        # Arrange
        project = self._project()

        # Act & Assert
        with pytest.raises(TypeError, match="create_documents"):
            project.create_documents("hello")

    def test_creates_one_document_per_text_under_this_project(self):
        """Each text becomes its own row, carrying this project's id."""
        # Arrange
        project = self._project()
        created = []

        def _create(session, document_create):
            created.append(document_create)
            return SimpleNamespace(id=uuid.uuid4())

        with (
            patch("geoparser.project.project.get_session"),
            patch(
                "geoparser.project.project.DocumentRepository.create",
                side_effect=_create,
            ),
        ):
            # Act
            project.create_documents(["first", "second"])

        # Assert
        assert [d.text for d in created] == ["first", "second"]
        assert [d.project_id for d in created] == [project.id, project.id]

    def test_returns_the_new_ids_in_input_order(self):
        """The returned IDs line up with the texts that were passed in."""
        # Arrange
        project = self._project()
        ids = [uuid.uuid4(), uuid.uuid4()]

        with (
            patch("geoparser.project.project.get_session"),
            patch(
                "geoparser.project.project.DocumentRepository.create",
                side_effect=[SimpleNamespace(id=i) for i in ids],
            ),
        ):
            # Act
            returned = project.create_documents(["first", "second"])

        # Assert
        assert returned == ids


@pytest.mark.unit
class TestEnsureProjectRecord:
    """Looking up or creating the project row."""

    def test_reuses_an_existing_project_of_the_same_name(self):
        """An existing project is looked up by name and its id reused."""
        # Arrange
        project = Project.__new__(Project)
        existing_id = uuid.uuid4()
        get_by_name = Mock(return_value=SimpleNamespace(id=existing_id))

        with (
            patch("geoparser.project.project.get_session"),
            patch(
                "geoparser.project.project.ProjectRepository.get_by_name", get_by_name
            ),
            patch("geoparser.project.project.ProjectRepository.create") as create,
        ):
            # Act
            found = project._ensure_project_record("demo")

        # Assert
        assert found == existing_id
        assert get_by_name.call_args.args[1] == "demo"
        create.assert_not_called()

    def test_creates_a_project_when_the_name_is_new(self):
        """A missing project is created with the requested name."""
        # Arrange
        project = Project.__new__(Project)
        new_id = uuid.uuid4()

        with (
            patch("geoparser.project.project.get_session"),
            patch(
                "geoparser.project.project.ProjectRepository.get_by_name",
                return_value=None,
            ),
            patch(
                "geoparser.project.project.ProjectRepository.create",
                return_value=SimpleNamespace(id=new_id),
            ) as create,
        ):
            # Act
            created = project._ensure_project_record("fresh")

        # Assert
        assert created == new_id
        assert create.call_args.args[1].name == "fresh"
