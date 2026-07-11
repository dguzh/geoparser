"""
Unit tests for geoparser/gazetteer/artifact.py

Tests the artifact-level helpers and the GazetteerArtifact class directly,
independent of the higher-level Gazetteer query interface.
"""

import pytest

from geoparser.gazetteer import artifact as artifact_module
from geoparser.gazetteer.artifact import GazetteerArtifact, artifact_path


@pytest.mark.unit
class TestGazetteersDir:
    """Test the gazetteers_dir() helper."""

    def test_uses_override_env_var(self, tmp_path, monkeypatch):
        """The GEOPARSER_GAZETTEERS_DIR env var overrides the default location."""
        monkeypatch.setenv("GEOPARSER_GAZETTEERS_DIR", str(tmp_path))

        assert artifact_module.gazetteers_dir() == tmp_path

    def test_defaults_to_user_data_dir(self, monkeypatch):
        """Without an override, the user data directory is used."""
        monkeypatch.delenv("GEOPARSER_GAZETTEERS_DIR", raising=False)

        result = artifact_module.gazetteers_dir()

        assert result.name == "gazetteers"
        assert "geoparser" in str(result)


@pytest.mark.unit
class TestListArtifacts:
    """Test the list_artifacts() helper."""

    def test_returns_empty_list_when_directory_missing(self, tmp_path, monkeypatch):
        """A missing gazetteers directory yields no artifacts."""
        monkeypatch.setenv("GEOPARSER_GAZETTEERS_DIR", str(tmp_path / "missing"))

        assert artifact_module.list_artifacts() == []

    def test_returns_sorted_artifact_names(self, tmp_path, monkeypatch):
        """Installed artifacts are returned sorted by name, without extension."""
        monkeypatch.setenv("GEOPARSER_GAZETTEERS_DIR", str(tmp_path))
        (tmp_path / f"zebra{artifact_module.ARTIFACT_SUFFIX}").touch()
        (tmp_path / f"alpha{artifact_module.ARTIFACT_SUFFIX}").touch()
        (tmp_path / "not-an-artifact.txt").touch()
        (tmp_path / "subdirectory").mkdir()

        assert artifact_module.list_artifacts() == ["alpha", "zebra"]


@pytest.mark.unit
class TestGazetteerArtifactInitialization:
    """Test GazetteerArtifact.__init__()."""

    def test_raises_when_file_missing(self, tmp_path):
        """Opening a non-existent artifact file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            GazetteerArtifact(tmp_path / "missing.db")

    def test_raises_when_file_is_not_a_database(self, tmp_path):
        """A file that isn't a valid SQLite database raises a clear RuntimeError."""
        path = tmp_path / "broken.db"
        path.write_text("not a sqlite database")

        with pytest.raises(RuntimeError, match="not a valid gazetteer artifact"):
            GazetteerArtifact(path)


@pytest.mark.unit
class TestGazetteerArtifactClose:
    """Test GazetteerArtifact.close()."""

    def test_close_after_use_releases_connection(self, make_artifact):
        """Closing after querying releases the thread-local connection."""
        make_artifact(name="testgaz")
        artifact = GazetteerArtifact(artifact_path("testgaz"))
        artifact.find("1")

        artifact.close()

        assert getattr(artifact._local, "connection", None) is None

    def test_close_without_prior_use_is_a_no_op(self, make_artifact):
        """Closing an artifact that never opened a connection does nothing."""
        make_artifact(name="testgaz")
        artifact = GazetteerArtifact(artifact_path("testgaz"))

        artifact.close()

        assert getattr(artifact._local, "connection", None) is None

    def test_reopens_a_new_connection_after_close(self, make_artifact):
        """Querying again after close() transparently opens a new connection."""
        make_artifact(name="testgaz")
        artifact = GazetteerArtifact(artifact_path("testgaz"))
        artifact.find("1")
        artifact.close()

        feature = artifact.find("1")

        assert feature is not None
