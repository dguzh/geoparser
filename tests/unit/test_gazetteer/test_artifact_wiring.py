"""
Tests for where artifacts live and what SQLite functions they get.

The fuzzy search in the gazetteer depends on two Python functions being
registered on every connection under the exact names the SQL uses, and on
them being declared deterministic so SQLite may use them in indexed queries.
"""

import sqlite3
from unittest.mock import Mock

import pytest

from geoparser.gazetteer.artifact import (
    ARTIFACT_SUFFIX,
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
