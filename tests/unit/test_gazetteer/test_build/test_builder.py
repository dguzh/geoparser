"""
Unit tests for geoparser/gazetteer/build/builder.py

Exercises GazetteerBuilder's internal helpers directly (memory sizing,
temp-directory handling, spatial extension loading) and runs small,
hand-crafted builds to trigger error paths (no features produced, a stale
leftover build directory) that are impractical to reach through the
public build() entry point alone.
"""

import os
import textwrap
from unittest.mock import MagicMock

import duckdb
import pytest

from geoparser.gazetteer import artifact
from geoparser.gazetteer.build.builder import GazetteerBuilder, _sqlite_tmpdir
from geoparser.gazetteer.build.schema import GazetteerConfig


@pytest.mark.unit
class TestSqliteTmpdir:
    """Test the _sqlite_tmpdir() context manager."""

    def test_sets_and_restores_previous_value(self, monkeypatch, tmp_path):
        """A pre-existing SQLITE_TMPDIR is restored after the context exits."""
        monkeypatch.setenv("SQLITE_TMPDIR", "/original/tmpdir")

        with _sqlite_tmpdir(tmp_path):
            assert os.environ["SQLITE_TMPDIR"] == str(tmp_path)

        assert os.environ["SQLITE_TMPDIR"] == "/original/tmpdir"

    def test_removes_var_when_none_was_set_before(self, monkeypatch, tmp_path):
        """SQLITE_TMPDIR is removed again if it wasn't set beforehand."""
        monkeypatch.delenv("SQLITE_TMPDIR", raising=False)

        with _sqlite_tmpdir(tmp_path):
            assert os.environ["SQLITE_TMPDIR"] == str(tmp_path)

        assert "SQLITE_TMPDIR" not in os.environ


@pytest.mark.unit
class TestMemoryLimit:
    """Test GazetteerBuilder._memory_limit_mb() and _physical_memory_bytes()."""

    def test_returns_none_when_physical_memory_is_unknown(self, monkeypatch):
        """No memory limit is set when the machine's RAM can't be determined."""
        builder = GazetteerBuilder()
        monkeypatch.setattr(builder, "_physical_memory_bytes", lambda: None)

        assert builder._memory_limit_mb() is None

    def test_returns_a_bounded_value_when_memory_is_known(self, monkeypatch):
        """A known RAM size yields a positive, bounded MiB limit."""
        builder = GazetteerBuilder()
        monkeypatch.setattr(
            builder, "_physical_memory_bytes", lambda: 8 * 1024 * 1024 * 1024
        )

        assert builder._memory_limit_mb() > 0

    def test_physical_memory_bytes_returns_none_on_error(self, monkeypatch):
        """A sysconf() failure is treated as 'unknown', not a crash."""

        def _raise(_name):
            raise OSError("not supported")

        monkeypatch.setattr(os, "sysconf", _raise)

        assert GazetteerBuilder._physical_memory_bytes() is None


@pytest.mark.unit
class TestLoadSpatialExtension:
    """Test GazetteerBuilder._load_spatial_extension()."""

    def test_wraps_duckdb_errors_in_a_clear_runtime_error(self):
        """A failure to install/load the extension raises a clear RuntimeError."""
        connection = MagicMock()
        connection.install_extension.side_effect = duckdb.Error("network unreachable")
        builder = GazetteerBuilder()

        with pytest.raises(
            RuntimeError, match="Failed to load the DuckDB spatial extension"
        ):
            builder._load_spatial_extension(connection)


@pytest.mark.unit
class TestBuildErrorPaths:
    """Test build() error paths that are hard to reach end-to-end."""

    def test_compile_features_raises_when_no_features_produced(self):
        """A source with zero rows produces zero features, which fails clearly.

        Builds the underlying DuckDB table directly (bypassing acquire/load)
        so the scenario doesn't depend on how the CSV reader handles an
        empty file.
        """
        connection = duckdb.connect()
        connection.execute("CREATE TABLE rows (rid VARCHAR, name VARCHAR)")
        config = GazetteerConfig.model_validate(
            {
                "name": "empty",
                "sources": [
                    {
                        "name": "rows",
                        "path": "unused.csv",
                        "file": "unused.csv",
                        "delimiter": "\t",
                        "attributes": [
                            {"name": "rid", "type": "text"},
                            {"name": "name", "type": "text"},
                        ],
                    }
                ],
                "features": [
                    {"source": "rows", "identifier": "rid", "names": ["name"]}
                ],
            }
        )
        builder = GazetteerBuilder()

        with pytest.raises(ValueError, match="produced no features"):
            builder._compile_features(connection, config)

    def test_rebuild_clears_a_stale_leftover_build_directory(
        self, tmp_path, monkeypatch
    ):
        """A leftover build directory from an earlier, interrupted build is
        cleared out rather than reused."""
        data_file = tmp_path / "peaks.csv"
        data_file.write_text("p1\tSummit\t800\n")
        config_file = tmp_path / "peaks.yaml"
        config_file.write_text(
            textwrap.dedent(
                """
                name: peaks
                sources:
                  - name: peaks
                    path: peaks.csv
                    file: peaks.csv
                    delimiter: "\\t"
                    quote: ""
                    attributes:
                      - name: pid
                        type: text
                      - name: name
                        type: text
                      - name: height
                        type: integer
                features:
                  - source: peaks
                    identifier: "pid"
                    names:
                      - "name"
                """
            )
        )
        gazetteers_dir = tmp_path / "gazetteers"
        monkeypatch.setenv("GEOPARSER_GAZETTEERS_DIR", str(gazetteers_dir))
        target_path = artifact.artifact_path("peaks")
        stale_build_dir = target_path.parent / ".build-peaks"
        stale_build_dir.mkdir(parents=True)
        (stale_build_dir / "leftover.txt").write_text("stale")

        GazetteerBuilder().build(config_file)

        assert target_path.exists()
        assert not stale_build_dir.exists()
