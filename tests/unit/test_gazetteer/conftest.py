"""
Fixtures for gazetteer unit tests.

Provides a factory that writes small, hand-crafted gazetteer artifacts into a
temporary gazetteers directory, so runtime classes can be tested without
running the build pipeline.
"""

import json
import sqlite3
import typing as t
from pathlib import Path

import pytest

from geoparser.gazetteer import artifact as artifact_module

DEFAULT_FEATURES = [
    {
        "identifier": "1",
        "source": "city",
        "data": {"name": "Paris", "population": 2100000},
        "names": ["Paris", "Lutetia"],
    },
    {
        "identifier": "2",
        "source": "city",
        "data": {"name": "Berlin", "population": 3600000},
        "names": ["Berlin"],
    },
    {
        "identifier": "3",
        "source": "city",
        "data": {"name": "Paris (Texas)", "population": 25000},
        "names": ["Paris (Texas)"],
    },
]


@pytest.fixture
def make_artifact(tmp_path: Path, monkeypatch) -> t.Callable:
    """
    Factory fixture that writes gazetteer artifacts into a temp directory.

    The temp directory is set as the gazetteers directory, so artifacts made
    by this factory are immediately visible to ``Gazetteer(name)``.
    """
    monkeypatch.setenv("GEOPARSER_GAZETTEERS_DIR", str(tmp_path))

    def _make(
        name: str = "testgaz",
        features: t.Optional[t.List[dict]] = None,
        crs: str = "EPSG:4326",
        schema_version: t.Optional[str] = None,
    ) -> Path:
        """
        Write an artifact with the given features.

        Each feature dict may define: identifier, source, data (dict),
        geometry (WKB bytes or None) and names (list of strings).
        """
        if features is None:
            features = DEFAULT_FEATURES
        path = tmp_path / f"{name}{artifact_module.ARTIFACT_SUFFIX}"
        connection = sqlite3.connect(path)
        artifact_module.register_functions(connection)
        for statement in artifact_module.BASE_SCHEMA:
            connection.execute(statement)
        for index, feature in enumerate(features, start=1):
            connection.execute(
                "INSERT INTO feature (id, identifier, source, data, geometry) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    index,
                    feature["identifier"],
                    feature.get("source", "place"),
                    json.dumps(feature.get("data", {})),
                    feature.get("geometry"),
                ),
            )
            for name_text in feature.get("names", []):
                connection.execute(
                    "INSERT INTO name (feature_id, text) VALUES (?, ?)",
                    (index, name_text),
                )
        for statement in artifact_module.SEARCH_SCHEMA:
            connection.execute(statement)
        metadata = {
            "schema_version": schema_version or artifact_module.SCHEMA_VERSION,
            "name": name,
            "crs": crs,
        }
        connection.executemany(
            "INSERT INTO metadata (key, value) VALUES (?, ?)",
            list(metadata.items()),
        )
        connection.commit()
        connection.close()
        return path

    return _make
