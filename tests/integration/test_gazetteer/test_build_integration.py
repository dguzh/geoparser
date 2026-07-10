"""
Integration tests for the gazetteer build pipeline.

Builds real artifacts from the Andorra fixture data and from small inline
configs (covering duplicate-identifier merging), and inspects the resulting
SQLite files through the runtime layer.
"""

import sqlite3
import textwrap

import pytest

from geoparser.gazetteer.artifact import GazetteerArtifact, artifact_path
from geoparser.gazetteer.build import GazetteerBuilder
from geoparser.gazetteer.build.builder import uninstall
from geoparser.gazetteer.gazetteer import Gazetteer


@pytest.mark.integration
class TestAndorraBuild:
    """Test the artifact built from the Andorra fixture config."""

    def test_artifact_is_installed(self, andorra_gazetteer):
        """The build produces an artifact in the gazetteers directory."""
        assert artifact_path("andorranames").exists()

    def test_artifact_metadata(self, andorra_gazetteer):
        """The artifact carries its name, CRS and counts as metadata."""
        artifact = GazetteerArtifact(artifact_path("andorranames"))

        assert artifact.name == "andorranames"
        assert artifact.crs == "EPSG:4326"
        assert int(artifact.metadata["feature_count"]) == artifact.count_features()
        assert int(artifact.metadata["name_count"]) == artifact.count_names()

    def test_features_and_names_are_populated(self, andorra_gazetteer):
        """The Andorra fixture produces a meaningful number of rows."""
        artifact = GazetteerArtifact(artifact_path("andorranames"))

        assert artifact.count_features() > 100
        assert artifact.count_names() > artifact.count_features()

    def test_identifiers_are_unique(self, andorra_gazetteer):
        """Every feature has a unique identifier."""
        connection = sqlite3.connect(artifact_path("andorranames"))
        try:
            total, distinct = connection.execute(
                "SELECT count(*), count(DISTINCT identifier) FROM feature"
            ).fetchone()
        finally:
            connection.close()

        assert total == distinct

    def test_split_names_are_registered(self, andorra_gazetteer):
        """Alternate names from the comma-separated column are searchable."""
        gazetteer = Gazetteer("andorranames")

        # "Andorre-la-Vieille" is an alternate name of Andorra la Vella
        results = gazetteer.search("Andorre-la-Vieille", method="exact")

        assert any(feature.identifier == "3041563" for feature in results)

    def test_expression_names_are_registered(self, andorra_gazetteer):
        """Names derived via expressions (parenthesis stripping) are searchable."""
        gazetteer = Gazetteer("andorranames")

        features_with_parens = [
            feature
            for feature in gazetteer.search("General", method="partial", tiers=3)
            if "(" in feature.data["name"]
        ]

        for feature in features_with_parens:
            stripped = feature.data["name"].split("(")[0].strip()
            assert stripped in feature.names

    def test_spatial_lookup_assigns_shape(self, andorra_gazetteer):
        """The spatial lookup tags features inside the Andorra boundary."""
        gazetteer = Gazetteer("andorranames")

        feature = gazetteer.find("3041563")  # Andorra la Vella

        assert feature.data["shape_fid"] is not None

    def test_uninstall_removes_artifact(
        self, andorra_config_path, tmp_path, monkeypatch
    ):
        """Uninstalling deletes the artifact file."""
        monkeypatch.setenv("GEOPARSER_GAZETTEERS_DIR", str(tmp_path))
        GazetteerBuilder().build(andorra_config_path)
        assert artifact_path("andorranames").exists()

        assert uninstall("andorranames") is True
        assert not artifact_path("andorranames").exists()
        assert uninstall("andorranames") is False


@pytest.mark.integration
class TestDuplicateIdentifierMerge:
    """Test merging of rows sharing an identifier."""

    @pytest.fixture
    def duplicates_config(self, tmp_path):
        """A config whose source repeats identifiers across rows."""
        data_file = tmp_path / "peaks.csv"
        data_file.write_text(
            "p1\tNorth Summit\t800\n" "p1\tSouth Summit\t1200\n" "p2\tLone Hill\t300\n"
        )
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
                    data:
                      - "name"
                      - "height"
                """
            )
        )
        return config_file

    def test_duplicate_identifiers_merge_into_one_feature(
        self, duplicates_config, tmp_path, monkeypatch
    ):
        """Duplicate rows become one feature with collected names."""
        monkeypatch.setenv("GEOPARSER_GAZETTEERS_DIR", str(tmp_path / "gazetteers"))
        GazetteerBuilder().build(duplicates_config)

        gazetteer = Gazetteer("peaks")
        merged = gazetteer.find("p1")

        assert merged is not None
        assert set(merged.names) == {"North Summit", "South Summit"}
        # Data values are taken from the first row of the group
        assert merged.data["name"] == "North Summit"
        assert merged.data["height"] == 800

        # Searching either name finds the same merged feature
        by_north = gazetteer.search("North Summit", method="exact")
        by_south = gazetteer.search("South Summit", method="exact")
        assert [f.identifier for f in by_north] == ["p1"]
        assert [f.identifier for f in by_south] == ["p1"]

    def test_artifact_has_one_row_per_identifier(
        self, duplicates_config, tmp_path, monkeypatch
    ):
        """The artifact stores exactly one feature row per identifier."""
        monkeypatch.setenv("GEOPARSER_GAZETTEERS_DIR", str(tmp_path / "gazetteers"))
        GazetteerBuilder().build(duplicates_config)

        artifact = GazetteerArtifact(artifact_path("peaks"))

        assert artifact.count_features() == 2


@pytest.mark.integration
class TestCrossBlockIdentifierCollision:
    """Test that identifier collisions across feature blocks fail the build."""

    def test_build_fails_with_clear_error(self, tmp_path, monkeypatch):
        """The same identifier across two feature blocks aborts the build."""
        data_file = tmp_path / "rows.csv"
        data_file.write_text("x1\tSomething\n")
        config_file = tmp_path / "clash.yaml"
        config_file.write_text(
            textwrap.dedent(
                """
                name: clash
                sources:
                  - name: rows_a
                    path: rows.csv
                    file: rows.csv
                    delimiter: "\\t"
                    quote: ""
                    attributes:
                      - name: rid
                        type: text
                      - name: name
                        type: text
                  - name: rows_b
                    path: rows.csv
                    file: rows.csv
                    delimiter: "\\t"
                    quote: ""
                    attributes:
                      - name: rid
                        type: text
                      - name: name
                        type: text
                features:
                  - source: rows_a
                    identifier: "rid"
                    names:
                      - "name"
                  - source: rows_b
                    identifier: "rid"
                    names:
                      - "name"
                """
            )
        )
        monkeypatch.setenv("GEOPARSER_GAZETTEERS_DIR", str(tmp_path / "gazetteers"))

        with pytest.raises(ValueError, match="unique across the whole gazetteer"):
            GazetteerBuilder().build(config_file)

        assert not artifact_path("clash").exists()
