import re
from pathlib import Path

import py
import pytest
from requests_mock.mocker import Mocker

from geoparser.geonames import GeoNames
from geoparser.tests.utils import get_static_test_file


@pytest.fixture
def geonames(tmpdir: py.path.LocalPath) -> GeoNames:
    gazetteer = GeoNames()
    gazetteer.data_dir = str(tmpdir)
    gazetteer.db_path = str(tmpdir / Path(gazetteer.db_path).name)
    return gazetteer


@pytest.mark.parametrize("keep_db", [True, False])
def test_clean_dir(geonames: GeoNames, keep_db: bool):
    # create db files and other file
    with open(geonames.db_path, "wb"), open(
        Path(geonames.db_path).parent / "other.txt", "w"
    ), open(Path(geonames.db_path).parent / "geonames.db-journal", "w"):
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
        assert n_files == 2
    if not keep_db:
        assert n_files == 0
    # always delete subdirectories
    assert n_dirs == 0


@pytest.mark.parametrize(
    "url, filename",
    [
        ("https://my.url.org/path/to/a.txt", "a.txt"),
        (
            "https://my.url.org/path/to/a.zip",
            "b.zip",
        ),
    ],
)
def test_download_file(
    geonames: GeoNames,
    url: str,
    filename: str,
    requests_mock: Mocker,
):
    print(type(requests_mock))
    with open(get_static_test_file(filename), "rb") as file:
        requests_mock.get(url, body=file)
        geonames.download_file(url=url)
    dir_content = Path(geonames.db_path).parent.glob("**/*")
    files = [content.name for content in dir_content]
    # a.txt downloaded as is, b.zip has been extracted
    assert files == [re.sub("zip", "txt", filename)]
