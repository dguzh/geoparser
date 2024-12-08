import json
import tempfile
from datetime import datetime
from pathlib import Path

import py
import pytest

from geoparser.annotator.sessions_cache import SessionsCache


@pytest.fixture(scope="function")
def sessions_cache() -> SessionsCache:
    cache = SessionsCache()
    cache.cache_dir = py.path.local(tempfile.mkdtemp())
    return cache


def test_file_path(sessions_cache: SessionsCache):
    test_id = "test"
    file_path = Path(sessions_cache.file_path(test_id))
    expected = Path(sessions_cache.cache_dir) / f"{test_id}.json"
    assert file_path == expected


def test_save(sessions_cache: SessionsCache):
    test_id = "save"
    test_dict = {"test": "test"}
    sessions_cache.save(test_id, test_dict)
    saved_path = Path(sessions_cache.cache_dir) / f"{test_id}.json"
    assert saved_path.is_file()
    with open(saved_path, "r") as infile:
        assert json.load(infile) == test_dict


@pytest.mark.parametrize("file_is", ["missing", "valid", "invalid"])
def test_load(capfd, sessions_cache: SessionsCache, file_is: str):
    test_id = f"load_{file_is}"
    test_dict = {"test": "test"}
    file_path = Path(sessions_cache.file_path(test_id))
    if file_is == "missing":
        assert sessions_cache.load(test_id) is None
    elif file_is == "valid":
        with open(file_path, "w") as outfile:
            outfile.write(json.dumps(test_dict))
        assert sessions_cache.load(test_id) == test_dict
    elif file_is == "invalid":
        with open(file_path, "w") as outfile:
            outfile.write("load")
            assert sessions_cache.load(test_id) == None
            out, _ = capfd.readouterr()
            assert f"Failed to load session {test_id}:" in out


@pytest.mark.parametrize("exists", [True, False])
def test_delete(sessions_cache: SessionsCache, exists: bool):
    test_id = f"delete_{exists}"
    test_dict = {"test": "test"}
    file_path = Path(sessions_cache.file_path(test_id))
    if exists:
        with open(file_path, "w") as outfile:
            outfile.write(json.dumps(test_dict))
        assert file_path.is_file()
        assert sessions_cache.delete(test_id) is True
    else:
        assert not file_path.is_file()
        assert sessions_cache.delete(test_id) is False
    assert not file_path.is_file()


def test_get_cached_sessions(sessions_cache: SessionsCache):
    def write_file(session: str, content: str):
        with open(sessions_cache.cache_dir / f"{session}.json", "w") as outfile:
            outfile.write(content)

    # 1. setup
    # valid session
    valid = {
        "session_id": "valid",
        "created_at": datetime.now().isoformat(),
        "last_updated": datetime.now().isoformat(),
        "gazetteer": "geonames",
        "num_documents": 1,
    }
    write_file(valid["session_id"], json.dumps(valid))
    # valid session with invalid create date format
    invalid_create = {
        "session_id": "invalid_create",
        "created_at": "0000000 today at 11 am",
        "last_updated": datetime.now().isoformat(),
        "gazetteer": "geonames",
        "num_documents": 1,
    }
    write_file(invalid_create["session_id"], json.dumps(invalid_create))
    # valid session with invalid update date format
    invalid_update = {
        "session_id": "invalid_update",
        "created_at": datetime.now().isoformat(),
        "last_updated": "0000000 today at 11 am",
        "gazetteer": "geonames",
        "num_documents": 1,
    }
    write_file(invalid_update["session_id"], json.dumps(invalid_update))
    # invalid json
    write_file("invalid", "asdf")

    # 2. assert results
    result = sessions_cache.get_cached_sessions()
    assert type(result) is list
    # the invalid file is not loaded
    assert len(result) == 3
    for elem in result:
        # all elements are valid sessions
        assert type(elem) is dict
        for key in [
            "session_id",
            "created_at",
            "last_updated",
            "gazetteer",
            "num_documents",
        ]:
            assert key
    # invalid_create is the most recent session with a valid update time code
    assert result[0]["session_id"] == "invalid_create"
