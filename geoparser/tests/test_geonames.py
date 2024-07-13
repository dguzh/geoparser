from pathlib import Path

import py
import pytest

from geoparser.geonames import GeoNames


@pytest.fixture
def geonames(tmpdir: py.path.LocalPath) -> GeoNames:
    gazetteer = GeoNames()
    gazetteer.data_dir = str(tmpdir)
    gazetteer.db_path = str(tmpdir / Path(gazetteer.db_path).name)
    return gazetteer
