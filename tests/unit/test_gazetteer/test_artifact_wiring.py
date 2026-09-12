"""
Tests for where artifacts live and what SQLite functions they get.

The fuzzy search in the gazetteer depends on two Python functions being
registered on every connection under the exact names the SQL uses, and on
them being declared deterministic so SQLite may use them in indexed queries.
"""

import re
import sqlite3
import threading
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from geoparser.gazetteer.artifact import (
    ARTIFACT_SUFFIX,
    GazetteerArtifact,
    artifact_path,
    gazetteers_dir,
    list_artifacts,
    register_functions,
)


@pytest.mark.unit
class TestGazetteersDir:
    """Where installed artifacts are looked for."""

    def test_defaults_under_a_geoparser_data_directory(self, monkeypatch):
        """The default location is namespaced to this application."""
        # Arrange
        monkeypatch.delenv("GEOPARSER_GAZETTEERS_DIR", raising=False)

        # Act
        directory = gazetteers_dir()

        # Assert
        assert "geoparser" in str(directory)
        assert directory.name == "gazetteers"

    def test_environment_variable_takes_precedence(self, monkeypatch, tmp_path):
        """An explicit override wins over the default location."""
        # Arrange
        monkeypatch.setenv("GEOPARSER_GAZETTEERS_DIR", str(tmp_path))

        # Act & Assert
        assert gazetteers_dir() == tmp_path

    def test_an_empty_override_falls_back_to_the_default(self, monkeypatch):
        """An empty value is treated as unset rather than as the root."""
        # Arrange
        monkeypatch.setenv("GEOPARSER_GAZETTEERS_DIR", "")

        # Act & Assert
        assert gazetteers_dir().name == "gazetteers"


@pytest.mark.unit
class TestArtifactPath:
    """Naming an artifact file."""

    def test_names_the_file_after_the_gazetteer(self, monkeypatch, tmp_path):
        """The artifact sits in the gazetteers directory under its own name."""
        # Arrange
        monkeypatch.setenv("GEOPARSER_GAZETTEERS_DIR", str(tmp_path))

        # Act & Assert
        assert (
            artifact_path("andorranames") == tmp_path / f"andorranames{ARTIFACT_SUFFIX}"
        )


@pytest.mark.unit
class TestListArtifacts:
    """Discovering installed gazetteers."""

    def test_returns_installed_names_sorted(self, monkeypatch, tmp_path):
        """Only artifact files count, and they come back by name."""
        # Arrange
        monkeypatch.setenv("GEOPARSER_GAZETTEERS_DIR", str(tmp_path))
        (tmp_path / f"zulu{ARTIFACT_SUFFIX}").touch()
        (tmp_path / f"alpha{ARTIFACT_SUFFIX}").touch()
        (tmp_path / "notes.txt").touch()

        # Act & Assert
        assert list_artifacts() == ["alpha", "zulu"]

    def test_returns_nothing_when_the_directory_is_absent(self, monkeypatch, tmp_path):
        """A machine with no gazetteers installed reports none."""
        # Arrange
        monkeypatch.setenv("GEOPARSER_GAZETTEERS_DIR", str(tmp_path / "missing"))

        # Act & Assert
        assert list_artifacts() == []


@pytest.mark.unit
class TestRegisterFunctions:
    """The SQL functions the fuzzy search relies on."""

    def test_registers_soundex_and_levenshtein_with_their_arities(self):
        """
        The names and argument counts are what the generated SQL calls.

        They are registered as deterministic so SQLite is free to use them in
        indexed queries; declaring otherwise silently degrades search.
        """
        # Arrange
        connection = Mock()

        # Act
        register_functions(connection)

        # Assert
        registered = {
            call.args[0]: (call.args[1], call.kwargs)
            for call in connection.create_function.call_args_list
        }
        assert registered["soundex"][0] == 1
        assert registered["levenshtein"][0] == 2
        assert registered["soundex"][1]["deterministic"] is True
        assert registered["levenshtein"][1]["deterministic"] is True

    def test_the_registered_functions_are_callable_from_sql(self):
        """A real connection can use both by name."""
        # Arrange
        connection = sqlite3.connect(":memory:")
        register_functions(connection)

        # Act
        soundex_value = connection.execute("SELECT soundex('Ashcraft')").fetchone()[0]
        distance = connection.execute(
            "SELECT levenshtein('kitten', 'sitting')"
        ).fetchone()[0]

        # Assert
        assert soundex_value == "A261"
        assert distance == 3


@pytest.mark.unit
class TestArtifactOpening:
    """Opening an artifact file."""

    def test_reports_a_missing_artifact_by_path(self, tmp_path):
        """The error names the file that could not be found."""
        # Arrange
        from geoparser.gazetteer.artifact import GazetteerArtifact

        missing = tmp_path / "absent.gazetteer"

        # Act & Assert
        with pytest.raises(FileNotFoundError, match=re.escape(str(missing))):
            GazetteerArtifact(missing)


@pytest.mark.unit
class TestArtifactConnection:
    """The per-thread, read-only SQLite connection."""

    @staticmethod
    def _artifact(tmp_path):
        """A minimal artifact whose metadata satisfies the version check."""
        from geoparser.gazetteer.artifact import SCHEMA_VERSION, GazetteerArtifact

        path = tmp_path / "mini.gazetteer"
        connection = sqlite3.connect(path)
        connection.execute("CREATE TABLE metadata (key TEXT, value TEXT)")
        connection.executemany(
            "INSERT INTO metadata VALUES (?, ?)",
            [
                ("schema_version", SCHEMA_VERSION),
                ("name", "mini"),
                ("crs", "EPSG:4326"),
            ],
        )
        connection.commit()
        connection.close()
        return GazetteerArtifact(path)

    def test_reuses_one_connection_within_a_thread(self, tmp_path):
        """
        The connection is cached on the thread-local under a fixed name.

        Looking it up under a different name would silently open a fresh
        connection on every query.
        """
        # Arrange
        artifact = self._artifact(tmp_path)

        # Act
        first = artifact._connection()
        second = artifact._connection()

        # Assert
        assert first is second

    def test_opens_the_artifact_read_only(self, tmp_path):
        """The artifact is never modified after the build."""
        # Arrange
        artifact = self._artifact(tmp_path)

        # Act & Assert
        with pytest.raises(sqlite3.OperationalError):
            artifact._connection().execute("CREATE TABLE scribble (x INTEGER)")

    def test_uses_sqlite_uri_mode_for_read_only_connections(
        self, tmp_path, monkeypatch
    ):
        """Opening a fresh connection must pass the read-only URI flag."""
        # Arrange
        artifact = self._artifact(tmp_path)
        artifact._local = threading.local()
        connect = Mock(wraps=sqlite3.connect)
        monkeypatch.setattr("geoparser.gazetteer.artifact.sqlite3.connect", connect)

        # Act
        connection = artifact._connection()

        # Assert
        assert connection.execute("SELECT COUNT(*) FROM metadata").fetchone()[0] == 3
        connect.assert_called_once_with(f"file:{artifact.path}?mode=ro", uri=True)

    def test_each_thread_gets_its_own_connection(self, tmp_path):
        """
        Threads do not share a connection, and using one off the creating
        thread is allowed.

        SQLite would otherwise refuse the cross-thread access outright.
        """
        # Arrange
        import threading

        artifact = self._artifact(tmp_path)
        main_connection = artifact._connection()
        other: list = []

        def _use_from_thread():
            other.append(artifact._connection())
            other.append(
                artifact._connection()
                .execute("SELECT COUNT(*) FROM metadata")
                .fetchone()[0]
            )

        # Act
        thread = threading.Thread(target=_use_from_thread)
        thread.start()
        thread.join()

        # Assert
        assert other[0] is not main_connection
        assert other[1] == 3


@pytest.mark.unit
class TestConnectionLifecycle:
    """Test the per-thread connection and its teardown."""

    def test_close_is_safe_before_any_query(self, make_artifact):
        """A freshly opened artifact has no connection yet, and close() copes."""
        artifact = GazetteerArtifact(make_artifact())
        # __init__ reads the metadata, so drop that connection to get back to
        # the state a thread that has never queried is in.
        artifact._local = threading.local()

        artifact.close()

        assert getattr(artifact._local, "connection", None) is None

    def test_close_lets_the_next_query_reconnect(self, make_artifact):
        """Closing releases the connection; the next query opens a fresh one."""
        artifact = GazetteerArtifact(make_artifact())
        first = artifact._connection()

        artifact.close()
        second = artifact._connection()

        assert second is not first
        assert artifact.count_features() == 3


@pytest.mark.unit
class TestFeatureRowMapping:
    """Test that artifact rows map onto the right Feature fields."""

    def test_id_and_identifier_come_from_different_columns(self, make_artifact):
        """The internal row id is distinct from the source's identifier."""
        artifact = GazetteerArtifact(
            make_artifact(
                features=[{"identifier": "geo-42", "names": ["Solothurn"]}],
            )
        )

        feature = artifact.find("geo-42")

        assert feature is not None
        assert feature.id == 1
        assert feature.identifier == "geo-42"


@pytest.mark.unit
class TestSearchDefaults:
    """Test the default limit and tier arguments of the search methods."""

    @pytest.mark.parametrize(
        "method",
        ["search_phrase", "search_partial", "search_fuzzy"],
    )
    def test_tiered_searches_default_to_one_tier_and_ten_thousand(
        self, make_artifact, method
    ):
        """Tiered searches score at most 10000 candidates and keep one tier."""
        artifact = GazetteerArtifact(make_artifact())
        captured = {}

        def record(matched_sql, parameters, limit, tiers):
            captured["limit"] = limit
            captured["tiers"] = tiers
            return []

        artifact._search_tiered = record

        getattr(artifact, method)("Paris")

        assert captured == {"limit": 10000, "tiers": 1}

    def test_search_exact_defaults_to_ten_thousand(self, make_artifact):
        """search_exact passes its default limit through to the query."""
        artifact = GazetteerArtifact(make_artifact())
        connection = artifact._connection()
        captured = []
        original = connection.execute

        def record(sql, parameters=()):
            captured.append(parameters)
            return original(sql, parameters)

        artifact._connection = lambda: SimpleNamespace(execute=record)

        artifact.search_exact("Paris")

        assert captured[0][-1] == 10000
