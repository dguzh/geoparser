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
from geoparser.gazetteer.build.builder import (
    GazetteerBuilder,
    _sqlite_temp_env_names,
    _sqlite_tmpdir,
)
from geoparser.gazetteer.build.schema import GazetteerConfig


@pytest.mark.unit
class TestSqliteTmpdir:
    """Test the _sqlite_tmpdir() context manager."""

    def test_unix_sets_and_restores_sqlite_tmpdir(self, monkeypatch, tmp_path):
        """On Unix, SQLITE_TMPDIR is set for the block and restored after."""
        monkeypatch.setattr(os, "name", "posix")
        monkeypatch.setenv("SQLITE_TMPDIR", "/original/tmpdir")

        with _sqlite_tmpdir(tmp_path):
            assert os.environ["SQLITE_TMPDIR"] == str(tmp_path)

        assert os.environ["SQLITE_TMPDIR"] == "/original/tmpdir"

    def test_unix_removes_var_when_none_was_set_before(self, monkeypatch, tmp_path):
        """On Unix, SQLITE_TMPDIR is removed again if it wasn't set beforehand."""
        monkeypatch.setattr(os, "name", "posix")
        monkeypatch.delenv("SQLITE_TMPDIR", raising=False)

        with _sqlite_tmpdir(tmp_path):
            assert os.environ["SQLITE_TMPDIR"] == str(tmp_path)

        assert "SQLITE_TMPDIR" not in os.environ

    def test_windows_sets_and_restores_tmp_and_temp(self, monkeypatch, tmp_path):
        """On Windows, TMP and TEMP are set (GetTempPath) and restored after."""
        monkeypatch.setattr(os, "name", "nt")
        monkeypatch.setenv("TMP", "C:\\original\\tmp")
        monkeypatch.setenv("TEMP", "C:\\original\\temp")
        monkeypatch.delenv("SQLITE_TMPDIR", raising=False)

        with _sqlite_tmpdir(tmp_path):
            assert os.environ["TMP"] == str(tmp_path)
            assert os.environ["TEMP"] == str(tmp_path)
            assert "SQLITE_TMPDIR" not in os.environ

        assert os.environ["TMP"] == "C:\\original\\tmp"
        assert os.environ["TEMP"] == "C:\\original\\temp"

    def test_windows_removes_tmp_vars_when_none_were_set_before(
        self, monkeypatch, tmp_path
    ):
        """On Windows, TMP/TEMP are removed again if they weren't set beforehand."""
        monkeypatch.setattr(os, "name", "nt")
        monkeypatch.delenv("TMP", raising=False)
        monkeypatch.delenv("TEMP", raising=False)

        with _sqlite_tmpdir(tmp_path):
            assert os.environ["TMP"] == str(tmp_path)
            assert os.environ["TEMP"] == str(tmp_path)

        assert "TMP" not in os.environ
        assert "TEMP" not in os.environ

    def test_env_names_match_platform(self, monkeypatch):
        """Unix steers SQLITE_TMPDIR; Windows steers TMP/TEMP."""
        monkeypatch.setattr(os, "name", "posix")
        assert _sqlite_temp_env_names() == ("SQLITE_TMPDIR",)

        monkeypatch.setattr(os, "name", "nt")
        assert _sqlite_temp_env_names() == ("TMP", "TEMP")


@pytest.mark.unit
class TestMemoryLimit:
    """Test memory/thread sizing helpers on GazetteerBuilder."""

    def test_returns_fallback_when_physical_memory_is_unknown(self, monkeypatch):
        """An undetectable RAM size still yields an explicit fallback limit."""
        builder = GazetteerBuilder()
        monkeypatch.setattr(builder, "_physical_memory_bytes", lambda: None)

        assert builder._memory_limit_mb() == GazetteerBuilder._FALLBACK_MEMORY_MB

    def test_returns_a_bounded_value_when_memory_is_known(self, monkeypatch):
        """A known RAM size yields a positive, bounded MiB limit."""
        builder = GazetteerBuilder()
        monkeypatch.setattr(
            builder, "_physical_memory_bytes", lambda: 8 * 1024 * 1024 * 1024
        )

        limit = builder._memory_limit_mb()
        assert limit > 0
        assert limit < 8 * 1024

    def test_thread_count_is_capped_by_memory_and_cpu(self, monkeypatch):
        """Thread count never exceeds CPU count or the memory budget."""
        builder = GazetteerBuilder()
        monkeypatch.setattr(os, "cpu_count", lambda: 8)

        assert builder._thread_count(512) == 1
        assert builder._thread_count(4096) == 4
        assert builder._thread_count(32_768) == 8

    def test_configure_staging_always_sets_memory_limit_and_threads(
        self, monkeypatch, tmp_path
    ):
        """Staging always applies an explicit memory_limit and threads value."""
        builder = GazetteerBuilder()
        monkeypatch.setattr(
            builder, "_physical_memory_bytes", lambda: 8 * 1024 * 1024 * 1024
        )
        monkeypatch.setattr(os, "cpu_count", lambda: 4)
        expected_limit = builder._memory_limit_mb()
        connection = duckdb.connect()
        try:
            builder._configure_staging(connection, tmp_path)
            memory_limit = connection.execute(
                "SELECT value FROM duckdb_settings() WHERE name = 'memory_limit'"
            ).fetchone()[0]
            threads = connection.execute(
                "SELECT value FROM duckdb_settings() WHERE name = 'threads'"
            ).fetchone()[0]
        finally:
            connection.close()

        # DuckDB may render/round the limit (e.g. ``4.5 GiB``); check we are
        # near the explicit budget rather than on DuckDB's unbounded default.
        actual_bytes = _setting_to_bytes(memory_limit)
        expected_bytes = expected_limit * 1024 * 1024
        assert actual_bytes > 0
        assert abs(actual_bytes - expected_bytes) / expected_bytes < 0.15
        assert int(threads) == 4

    def test_physical_memory_bytes_falls_back_to_windows_api(self, monkeypatch):
        """When sysconf is unavailable, the Windows reader is used."""

        def _no_sysconf():
            raise AttributeError("no sysconf")

        monkeypatch.setattr(
            GazetteerBuilder,
            "_physical_memory_bytes_sysconf",
            staticmethod(_no_sysconf),
        )
        monkeypatch.setattr(
            GazetteerBuilder,
            "_physical_memory_bytes_windows",
            staticmethod(lambda: 16 * 1024 * 1024 * 1024),
        )

        assert GazetteerBuilder._physical_memory_bytes() == 16 * 1024 * 1024 * 1024

    def test_physical_memory_bytes_returns_none_when_all_readers_fail(
        self, monkeypatch
    ):
        """All detection failures are treated as 'unknown', not a crash."""

        def _sysconf_error():
            raise OSError("not supported")

        def _windows_error():
            raise AttributeError("no windll")

        monkeypatch.setattr(
            GazetteerBuilder,
            "_physical_memory_bytes_sysconf",
            staticmethod(_sysconf_error),
        )
        monkeypatch.setattr(
            GazetteerBuilder,
            "_physical_memory_bytes_windows",
            staticmethod(_windows_error),
        )

        assert GazetteerBuilder._physical_memory_bytes() is None


def _setting_to_bytes(value: str) -> int:
    """Parse a DuckDB memory setting such as ``4.7GB`` or ``4915MB`` to bytes."""
    units = {
        "B": 1,
        "KB": 1000,
        "MB": 1000**2,
        "GB": 1000**3,
        "TB": 1000**4,
        "KIB": 1024,
        "MIB": 1024**2,
        "GIB": 1024**3,
        "TIB": 1024**4,
    }
    cleaned = value.strip().upper().replace(" ", "")
    for suffix, factor in sorted(units.items(), key=lambda item: -len(item[0])):
        if cleaned.endswith(suffix):
            return int(float(cleaned[: -len(suffix)]) * factor)
    raise AssertionError(f"Unrecognized DuckDB memory setting: {value!r}")


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
