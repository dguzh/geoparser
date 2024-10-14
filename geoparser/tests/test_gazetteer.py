import sqlite3
import tempfile
from pathlib import Path

import pandas as pd
import py
import pytest
from requests_mock.mocker import Mocker

from geoparser.config.models import Column, GazetteerData
from geoparser.gazetteer import LocalDBGazetteer
from geoparser.tests.utils import get_static_test_file, make_concrete


@pytest.fixture(scope="function")
def localdb_gazetteer(monkeypatch) -> LocalDBGazetteer:
    monkeypatch.setattr(
        "geoparser.config.config.get_config_file",
        lambda _: get_static_test_file("gazetteers_config_valid.yaml"),
    )
    localdb_gazetteer = make_concrete(LocalDBGazetteer)(gazetteer_name="test-full")
    tmpdir = py.path.local(tempfile.mkdtemp())
    localdb_gazetteer.data_dir = str(tmpdir)
    localdb_gazetteer.db_path = str(tmpdir / Path(localdb_gazetteer.db_path).name)
    localdb_gazetteer.clean_dir()
    return localdb_gazetteer


@pytest.mark.parametrize("keep_db", [True, False])
def test_clean_dir(localdb_gazetteer: LocalDBGazetteer, keep_db: bool):
    # create db files and other file
    with open(localdb_gazetteer.db_path, "wb"), open(
        Path(localdb_gazetteer.db_path).parent / "other.txt", "w"
    ), open(Path(localdb_gazetteer.db_path).parent / "geonames.db-journal", "w"):
        pass
    # create subdirectory
    (Path(localdb_gazetteer.db_path).parent / "subdir").mkdir(
        parents=True, exist_ok=True
    )
    # clean tmpdir
    localdb_gazetteer.clean_dir(keep_db=keep_db)
    dir_content = Path(localdb_gazetteer.db_path).parent.glob("**/*")
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
    "dataset",
    [
        GazetteerData(
            name="a",
            url="https://my.url.org/path/to/a.txt",
            extracted_files=["a.txt"],
            columns=[Column(name="", type="")],
        ),
        GazetteerData(
            name="b",
            url="https://my.url.org/path/to/b.zip",
            extracted_files=["b.txt"],
            columns=[Column(name="", type="")],
        ),
    ],
)
def test_download_file(
    localdb_gazetteer: LocalDBGazetteer,
    dataset: GazetteerData,
    requests_mock: Mocker,
):
    raw_file = dataset.url.split("/")[-1]
    with open(get_static_test_file(raw_file), "rb") as file:
        requests_mock.get(dataset.url, body=file)
        localdb_gazetteer.download_file(dataset=dataset)
    dir_content = Path(localdb_gazetteer.db_path).parent.glob("**/*")
    files = [content.name for content in dir_content]
    # a.txt downloaded as is, b.zip has been extracted and is still around
    zipfile = [raw_file] if raw_file.endswith(".zip") else []
    assert sorted(files) == sorted(dataset.extracted_files + zipfile)


def test_initiate_connection(localdb_gazetteer: LocalDBGazetteer):
    localdb_gazetteer._initiate_connection()
    assert type(localdb_gazetteer.conn) == sqlite3.Connection


def test_close_connection(localdb_gazetteer: LocalDBGazetteer):
    localdb_gazetteer._initiate_connection()
    localdb_gazetteer._close_connection()
    # sqlite3.ProgrammingError is raised when committing on closed db
    with pytest.raises(sqlite3.ProgrammingError):
        localdb_gazetteer._commit()


def test_get_cursor(localdb_gazetteer: LocalDBGazetteer):
    localdb_gazetteer._initiate_connection()
    assert type(localdb_gazetteer._get_cursor()) == sqlite3.Cursor


def test_execute_query(localdb_gazetteer: LocalDBGazetteer):
    query1 = "CREATE TABLE IF NOT EXISTS asdf (asdf TEXT)"
    query2 = "SELECT name FROM sqlite_master"
    localdb_gazetteer.execute_query(query1)
    tables = [table for table in localdb_gazetteer.execute_query(query2)[0]]
    assert ["asdf"] == tables
