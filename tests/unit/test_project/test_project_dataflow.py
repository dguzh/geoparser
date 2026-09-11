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


@pytest.mark.unit
class TestLoadAnnotations:
    """Importing an annotator export into the project."""

    @staticmethod
    def _export(tmp_path, documents, gazetteer="geonames"):
        """Write an annotator-format JSON file and return its path."""
        import json

        path = tmp_path / "annotations.json"
        path.write_text(json.dumps({"gazetteer": gazetteer, "documents": documents}))
        return path

    @staticmethod
    def _load(project, path, **kwargs):
        """Run load_annotations, capturing the two registration calls."""
        with (
            patch.object(project, "create_documents") as create_documents,
            patch.object(project, "create_references") as create_references,
            patch.object(project, "create_referents") as create_referents,
        ):
            project.load_annotations(str(path), "annotator_a", **kwargs)
        return create_documents, create_references, create_referents

    def test_registers_every_toponym_as_a_reference(self, tmp_path):
        """Spans come through per document, in file order."""
        # Arrange
        project = Project.__new__(Project)
        path = self._export(
            tmp_path,
            [
                {
                    "text": "Paris and Berlin",
                    "toponyms": [
                        {"start": 0, "end": 5, "loc_id": "1"},
                        {"start": 10, "end": 16, "loc_id": "2"},
                    ],
                },
                {"text": "Rome", "toponyms": [{"start": 0, "end": 4, "loc_id": "3"}]},
            ],
        )

        # Act
        _, create_references, _ = self._load(project, path)

        # Assert
        texts, references, tag = create_references.call_args.args
        assert texts == ["Paris and Berlin", "Rome"]
        assert references == [[(0, 5), (10, 16)], [(0, 4)]]
        assert tag == "annotator_a"

    def test_pairs_geocoded_toponyms_with_the_files_gazetteer(self, tmp_path):
        """Referents name the gazetteer the export declares."""
        # Arrange
        project = Project.__new__(Project)
        path = self._export(
            tmp_path,
            [{"text": "Paris", "toponyms": [{"start": 0, "end": 5, "loc_id": "7"}]}],
            gazetteer="swissnames3d",
        )

        # Act
        _, _, create_referents = self._load(project, path)

        # Assert
        texts, references, referents, tag = create_referents.call_args.args
        assert texts == ["Paris"]
        assert references == [[(0, 5)]]
        assert referents == [[("swissnames3d", "7")]]
        assert tag == "annotator_a"

    def test_keeps_ungeocoded_toponyms_as_references_without_referents(self, tmp_path):
        """
        A toponym left ungeocoded still counts as a reference.

        The two lists stay aligned by carrying None in the referent slot, so
        the resolver skips it rather than the reference disappearing.
        """
        # Arrange
        project = Project.__new__(Project)
        path = self._export(
            tmp_path,
            [
                {
                    "text": "Paris and Nowhere",
                    "toponyms": [
                        {"start": 0, "end": 5, "loc_id": "1"},
                        {"start": 10, "end": 17, "loc_id": ""},
                    ],
                }
            ],
        )

        # Act
        _, create_references, create_referents = self._load(project, path)

        # Assert
        assert create_references.call_args.args[1] == [[(0, 5), (10, 17)]]
        assert create_referents.call_args.args[2] == [[("geonames", "1"), None]]

    def test_does_not_create_documents_by_default(self, tmp_path):
        """Annotations attach to documents that already exist."""
        # Arrange
        project = Project.__new__(Project)
        path = self._export(
            tmp_path,
            [{"text": "Paris", "toponyms": [{"start": 0, "end": 5, "loc_id": "1"}]}],
        )

        # Act
        create_documents, _, _ = self._load(project, path)

        # Assert
        create_documents.assert_not_called()

    def test_creates_documents_from_the_export_when_asked(self, tmp_path):
        """With create_documents=True the texts are inserted first."""
        # Arrange
        project = Project.__new__(Project)
        path = self._export(
            tmp_path,
            [{"text": "Paris", "toponyms": [{"start": 0, "end": 5, "loc_id": "1"}]}],
        )

        # Act
        create_documents, _, _ = self._load(project, path, create_documents=True)

        # Assert
        create_documents.assert_called_once_with(["Paris"])


@pytest.mark.unit
class TestRunModules:
    """Running a module and recording it against a tag."""

    @staticmethod
    def _project() -> Project:
        """A Project with the database untouched."""
        project = Project.__new__(Project)
        project.id = uuid.uuid4()
        project.context = Mock()
        return project

    def test_records_the_recognizer_against_the_default_tag(self):
        """Omitting the tag files the run under "latest"."""
        # Arrange
        project = self._project()
        recognizer = Mock(id="rec-1")

        with (
            patch.object(project, "get_documents", return_value=[]),
            patch("geoparser.project.project.RecognitionService"),
        ):
            # Act
            project.run_recognizer(recognizer)

        # Assert
        project.context.update_recognizer_context.assert_called_once_with(
            "latest", "rec-1"
        )

    def test_records_the_recognizer_against_an_explicit_tag(self):
        """A caller-supplied tag is used verbatim."""
        # Arrange
        project = self._project()
        recognizer = Mock(id="rec-1")

        with (
            patch.object(project, "get_documents", return_value=[]),
            patch("geoparser.project.project.RecognitionService"),
        ):
            # Act
            project.run_recognizer(recognizer, tag="experiment")

        # Assert
        project.context.update_recognizer_context.assert_called_once_with(
            "experiment", "rec-1"
        )

    def test_runs_the_recognizer_over_the_projects_documents(self):
        """The service is handed the documents this project holds."""
        # Arrange
        project = self._project()
        documents = [Mock(), Mock()]

        with (
            patch.object(project, "get_documents", return_value=documents),
            patch("geoparser.project.project.RecognitionService") as service,
        ):
            # Act
            project.run_recognizer(Mock(id="rec-1"))

        # Assert
        service.return_value.predict.assert_called_once_with(documents)

    def test_records_the_resolver_against_the_default_tag(self):
        """The resolver path files under "latest" too."""
        # Arrange
        project = self._project()
        resolver = Mock(id="res-1")

        with (
            patch.object(project, "get_documents", return_value=[]),
            patch("geoparser.project.project.ResolutionService"),
        ):
            # Act
            project.run_resolver(resolver)

        # Assert
        project.context.update_resolver_context.assert_called_once_with(
            "latest", "res-1"
        )

    def test_runs_the_resolver_over_the_projects_documents(self):
        """The resolution service sees the same documents."""
        # Arrange
        project = self._project()
        documents = [Mock()]

        with (
            patch.object(project, "get_documents", return_value=documents),
            patch("geoparser.project.project.ResolutionService") as service,
        ):
            # Act
            project.run_resolver(Mock(id="res-1"), tag="experiment")

        # Assert
        service.return_value.predict.assert_called_once_with(documents)
        project.context.update_resolver_context.assert_called_once_with(
            "experiment", "res-1"
        )


@pytest.mark.unit
class TestGetDocumentsTag:
    """Which tag's results a retrieval is scoped to."""

    def test_defaults_to_the_latest_tag(self):
        """Both contexts are looked up for "latest" unless told otherwise."""
        # Arrange
        project = Project.__new__(Project)
        project.id = uuid.uuid4()
        project.context = Mock()
        project.context.get_recognizer_context.return_value = None
        project.context.get_resolver_context.return_value = None

        with (
            patch("geoparser.project.project.get_session"),
            patch(
                "geoparser.project.project.DocumentRepository.get_by_project",
                return_value=[],
            ),
        ):
            # Act
            project.get_documents()

        # Assert
        project.context.get_recognizer_context.assert_called_once_with("latest")
        project.context.get_resolver_context.assert_called_once_with("latest")

    def test_uses_an_explicit_tag_for_both_contexts(self):
        """A named tag scopes the recognizer and resolver together."""
        # Arrange
        project = Project.__new__(Project)
        project.id = uuid.uuid4()
        project.context = Mock()
        project.context.get_recognizer_context.return_value = None
        project.context.get_resolver_context.return_value = None

        with (
            patch("geoparser.project.project.get_session"),
            patch(
                "geoparser.project.project.DocumentRepository.get_by_project",
                return_value=[],
            ),
        ):
            # Act
            project.get_documents(tag="experiment")

        # Assert
        project.context.get_recognizer_context.assert_called_once_with("experiment")
        project.context.get_resolver_context.assert_called_once_with("experiment")
