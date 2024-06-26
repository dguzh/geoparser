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


@pytest.mark.parametrize("keep_db", [True, False])
def test_clean_dir(geonames: GeoNames, keep_db: bool):
    # create db and other file
    with open(geonames.db_path, "wb"), open(
        Path(geonames.db_path).parent / "other.txt", "w"
    ):
        pass
    # create subdirectory
    (Path(geonames.db_path).parent / "subdir").mkdir(parents=True, exist_ok=True)
    # clean tmpdir
    geonames.clean_dir(keep_db=keep_db)
    dir_content = Path(geonames.db_path).parent.glob("**/*")
    n_files = len([content for content in dir_content if content.is_file()])
    n_dirs = len([content for content in dir_content if content.is_dir()])
    # only keep db file
    if keep_db:
        assert n_files == 1
    if not keep_db:
        assert n_files == 0
    # always delete subdirectories
    assert n_dirs == 0
