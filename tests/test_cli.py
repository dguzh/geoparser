import pytest
from typer.testing import CliRunner

from geoparser.annotator import GeoparserAnnotator
from geoparser.cli import app
from geoparser.constants import GAZETTEERS_CHOICES
from geoparser.gazetteers.gazetteer import LocalDBGazetteer

runner = CliRunner()


@pytest.mark.parametrize("gazetteer", ["geonames", "swissnames3d", "nonexisting"])
def test_download(gazetteer: str, monkeypatch):
    valid_gazetteers = [e.value for e in GAZETTEERS_CHOICES]
    monkeypatch.setattr(
        LocalDBGazetteer, "setup_database", lambda *args, **kwargs: None
    )
    result = runner.invoke(app, ["download", gazetteer])
    # cli will return OK code with supported gazetteer
    if gazetteer in valid_gazetteers:
        assert result.exit_code == 0
    # unsupported gazetteer leads to error
    else:
        assert result.exit_code == 2


def test_annotator(monkeypatch):
    monkeypatch.setattr(GeoparserAnnotator, "run", lambda *args, **kwargs: None)
    result = runner.invoke(app, ["annotator"])
    # cli will always return OK code
    assert result.exit_code == 0


def test_unsupported_command():
    result = runner.invoke(app, ["unsupported_command"])
    # unsupported command leads to error
    assert result.exit_code == 2
