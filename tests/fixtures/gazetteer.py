"""
Gazetteer fixtures for testing.

Provides fixtures for working with the Andorra gazetteer in tests. The
gazetteer is built once per test session into a temporary gazetteers
directory; individual tests activate it by pointing the
``GEOPARSER_GAZETTEERS_DIR`` environment variable at that directory.
"""

import os
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def andorra_config_path() -> Path:
    """
    Get the path to the Andorra gazetteer configuration file.

    Returns:
        Path to andorranames.yaml configuration file
    """
    return Path(__file__).parent / "gazetteer" / "andorranames.yaml"


@pytest.fixture(scope="session")
def session_gazetteers_dir(tmp_path_factory, andorra_config_path: Path) -> Path:
    """
    Build the Andorra gazetteer artifact once for the whole test session.

    Returns:
        Path to a temporary gazetteers directory containing the artifact
    """
    from geoparser.gazetteer.build import GazetteerBuilder

    directory = tmp_path_factory.mktemp("gazetteers")
    original = os.environ.get("GEOPARSER_GAZETTEERS_DIR")
    os.environ["GEOPARSER_GAZETTEERS_DIR"] = str(directory)
    try:
        GazetteerBuilder().build(andorra_config_path)
    finally:
        if original is None:
            os.environ.pop("GEOPARSER_GAZETTEERS_DIR", None)
        else:
            os.environ["GEOPARSER_GAZETTEERS_DIR"] = original
    return directory


@pytest.fixture(scope="function")
def andorra_gazetteer(session_gazetteers_dir: Path, monkeypatch) -> None:
    """
    Make the pre-built Andorra gazetteer available to the test.

    Points the gazetteers directory at the session-scoped build so that
    ``Gazetteer("andorranames")`` resolves to the test artifact instead of
    any gazetteers installed on the machine.
    """
    monkeypatch.setenv("GEOPARSER_GAZETTEERS_DIR", str(session_gazetteers_dir))
