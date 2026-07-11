"""
Unit tests for geoparser/gazetteer/build/stages/emit.py

Tests row copying from DuckDB to SQLite, and building the artifact's search
structures and metadata, against small in-memory/temporary databases.
"""

import duckdb
import pytest

from geoparser.gazetteer.build.progress import item
from geoparser.gazetteer.build.schema import GazetteerConfig
from geoparser.gazetteer.build.stages.emit import (
    copy_rows,
    create_artifact_db,
    emit,
    finalize,
)


def minimal_config(**overrides) -> GazetteerConfig:
    """A minimal valid GazetteerConfig; only .name and .crs matter here."""
    data = {
        "name": "testgaz",
        "sources": [
            {
                "name": "places",
                "path": "places.csv",
                "file": "places.csv",
                "delimiter": ",",
                "attributes": [{"name": "id", "type": "integer"}],
            }
        ],
        "features": [{"source": "places", "identifier": "id", "names": ["id"]}],
    }
    data.update(overrides)
    return GazetteerConfig.model_validate(data)


@pytest.fixture
def duckdb_connection():
    connection = duckdb.connect()
    yield connection
    connection.close()


@pytest.fixture
def sqlite_connection(tmp_path):
    connection = create_artifact_db(tmp_path / "artifact.db")
    yield connection
    connection.close()


@pytest.mark.unit
class TestCreateArtifactDb:
    """Test create_artifact_db()."""

    def test_creates_fresh_database_with_base_schema(self, tmp_path):
        """A new artifact file gets the feature/name/metadata base schema."""
        connection = create_artifact_db(tmp_path / "artifact.db")

        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        connection.close()

        assert {"metadata", "feature", "name"} <= tables

    def test_overwrites_an_existing_file(self, tmp_path):
        """A pre-existing file at the target path is replaced, not appended to."""
        path = tmp_path / "artifact.db"
        path.write_text("not a real sqlite database")

        connection = create_artifact_db(path)
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        connection.close()

        assert {"metadata", "feature", "name"} <= tables


@pytest.mark.unit
class TestCopyRows:
    """Test copy_rows()."""

    def test_copies_all_rows_in_batches(self, duckdb_connection, sqlite_connection):
        """Every source row ends up in the destination table."""
        duckdb_connection.execute("CREATE TABLE src (id INTEGER, label VARCHAR)")
        duckdb_connection.execute(
            "INSERT INTO src VALUES (1, 'a'), (2, 'b'), (3, 'c')"
        )
        sqlite_connection.execute("CREATE TABLE dest (id INTEGER, label TEXT)")

        with item("Copying", total=100) as bar:
            copied = copy_rows(
                duckdb_connection,
                sqlite_connection,
                "SELECT id, label FROM src",
                "INSERT INTO dest (id, label) VALUES (?, ?)",
                bar,
            )

        assert copied == 3
        assert sqlite_connection.execute(
            "SELECT count(*) FROM dest"
        ).fetchone()[0] == 3

    def test_handles_a_query_with_no_rows(self, duckdb_connection, sqlite_connection):
        """An empty source query copies zero rows without error."""
        duckdb_connection.execute("CREATE TABLE src (id INTEGER, label VARCHAR)")
        sqlite_connection.execute("CREATE TABLE dest (id INTEGER, label TEXT)")

        with item("Copying", total=100) as bar:
            copied = copy_rows(
                duckdb_connection,
                sqlite_connection,
                "SELECT id, label FROM src",
                "INSERT INTO dest (id, label) VALUES (?, ?)",
                bar,
            )

        assert copied == 0
        assert sqlite_connection.execute("SELECT count(*) FROM dest").fetchone()[0] == 0


@pytest.mark.unit
class TestEmit:
    """Test emit()."""

    def test_copies_features_and_names(self, duckdb_connection, sqlite_connection):
        """Rows from the build tables are copied into the artifact tables."""
        duckdb_connection.execute(
            "CREATE TABLE _features_final (id INTEGER, identifier VARCHAR, "
            "source VARCHAR, data VARCHAR, geometry BLOB)"
        )
        duckdb_connection.execute(
            "INSERT INTO _features_final VALUES (1, 'a', 'city', '{}', NULL)"
        )
        duckdb_connection.execute(
            "CREATE TABLE _names_final (feature_id INTEGER, text VARCHAR)"
        )
        duckdb_connection.execute("INSERT INTO _names_final VALUES (1, 'Alpha')")

        feature_count, name_count = emit(duckdb_connection, sqlite_connection)

        assert feature_count == 1
        assert name_count == 1
        assert sqlite_connection.execute(
            "SELECT count(*) FROM feature"
        ).fetchone()[0] == 1
        assert sqlite_connection.execute(
            "SELECT count(*) FROM name"
        ).fetchone()[0] == 1


@pytest.mark.unit
class TestFinalize:
    """Test finalize()."""

    def _populate(self, sqlite_connection) -> None:
        sqlite_connection.execute(
            "INSERT INTO feature (id, identifier, source, data, geometry) "
            "VALUES (1, 'a', 'city', '{}', NULL)"
        )
        sqlite_connection.execute(
            "INSERT INTO name (feature_id, text) VALUES (1, 'Alpha')"
        )

    def test_builds_search_structures_and_metadata(self, sqlite_connection):
        """A consistent artifact gets its indexes, FTS, soundex and metadata."""
        self._populate(sqlite_connection)

        finalize(sqlite_connection, minimal_config(), feature_count=1, name_count=1)

        metadata = dict(
            sqlite_connection.execute("SELECT key, value FROM metadata").fetchall()
        )
        assert metadata["name"] == "testgaz"
        assert metadata["feature_count"] == "1"
        assert metadata["name_count"] == "1"
        assert (
            sqlite_connection.execute(
                "SELECT text FROM name_fts WHERE name_fts MATCH 'Alpha'"
            ).fetchone()
            is not None
        )

    def test_raises_when_stored_counts_mismatch_expected(self, sqlite_connection):
        """A mismatch between expected and stored rows fails integrity checks."""
        self._populate(sqlite_connection)

        with pytest.raises(RuntimeError, match="integrity check failed"):
            finalize(sqlite_connection, minimal_config(), feature_count=2, name_count=1)
