import io
import json
import re
import tempfile
import uuid
from datetime import datetime

import py
import pytest
from fastapi.testclient import TestClient
from werkzeug.wrappers import Response

from geoparser.annotator.app import annotator, app, get_session, sessions_cache
from geoparser.constants import DEFAULT_SESSION_SETTINGS
from tests.utils import get_static_test_file


@pytest.fixture(scope="function")
def client(monkeypatch):
    tmpdir = tempfile.mkdtemp()
    monkeypatch.setattr(
        sessions_cache,
        "file_path",
        lambda session_id: py.path.local(tmpdir) / f"{session_id}.json",
    )
    return TestClient(app)


def validate_json_response(
    response: Response, expected_status_code: int, expected_json: dict
):
    if expected_status_code:
        assert response.status_code == expected_status_code
    if expected_json:
        assert (
            bytes(
                json.dumps(expected_json, separators=(",", ":")),
                encoding="utf8",
            )
            in response.content
        )


def set_session(session_id: str, *, settings=None, **document_kwargs) -> dict:
    session = {
        **get_session("geonames"),
        **{
            "session_id": session_id,
            "documents": [
                {
                    "filename": "test.txt",
                    "spacy_applied": False,
                    "spacy_model": "en_core_web_sm",
                    "text": "Andorra is nice.",
                    "toponyms": [
                        {"end": 7, "loc_id": "", "start": 0, "text": "Andorra"},
                    ],
                }
            ],
        },
    }
    if settings:
        session["settings"] = settings
    for key, value in document_kwargs.items():
        session["documents"][0][key] = value
    sessions_cache.save(session["session_id"], session)
    return session


def test_get_session():
    gazetteer = "geonames"
    session = get_session(gazetteer)
    assert type(session) is dict
    # valid uuid (would raise Error if not)
    uuid.UUID(session["session_id"])
    # valid datetime strings
    for date_field in ["created_at", "last_updated"]:
        assert datetime.fromisoformat(session[date_field])
    # gazetteer is the one specified
    assert session["gazetteer"] == gazetteer
    # default settings are applied initially
    assert session["settings"] == DEFAULT_SESSION_SETTINGS
    # documents are empty list
    assert type(session["documents"]) is list
    assert len(session["documents"]) == 0


def test_index(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    # no errors: returns index html template
    assert b"<title>Geoparser Annotator</title>" in response.content


def test_start_new_session(client: TestClient):
    response = client.get("/start_new_session")
    assert response.status_code == 200
    # no errors: returns start_new_session html template
    assert b"<title>Start New Session</title>" in response.content


def test_continue_session(client: TestClient):
    response = client.get("/continue_session")
    assert response.status_code == 200
    # no errors: returns continue_session html template
    assert b"<title>Continue Session</title>" in response.content


@pytest.mark.parametrize("valid_session", [True, False])
@pytest.mark.parametrize("doc_index", [0, 1])
def test_annotate(client: TestClient, valid_session: bool, doc_index: int):
    session_id = "annotate"
    if valid_session:
        set_session(session_id)
    response = client.get(
        f"/session/{session_id}/document/{doc_index}/annotate", follow_redirects=False
    )
    # redirect to index if session is invalid
    if not valid_session:
        assert response.status_code == 302
        assert response.next_request.url == "http://testserver/"
    # invalid doc_index always redirects to 0
    elif valid_session and doc_index == 1:
        assert response.status_code == 302
        assert (
            response.next_request.url
            == "http://testserver/session/annotate/document/0/annotate"
        )
    # vaild doc_index returns the annotate page
    elif valid_session and doc_index == 0:
        assert response.status_code == 200


def test_create_session(client: TestClient):
    filename = "annotator_doc0.txt"
    response = client.post(
        "/session",
        data={
            "gazetteer": "geonames",
            "spacy_model": "en_core_web_sm",
        },
        files=[("files", (filename, open(get_static_test_file(filename), "rb")))],
        follow_redirects=False,
    )
    assert response.status_code == 302
    # redirected to annotate page for first document
    assert re.search(
        r"http:\/\/testserver\/session\/.*\/document\/0\/annotate",
        str(response.next_request.url),
    )


@pytest.mark.parametrize("cached_session", ["bad_session", "test_load_cached"])
@pytest.mark.parametrize("file_exists", [True, False])
def test_continue_session_cached(
    client: TestClient, cached_session: str, file_exists: bool
):
    if file_exists and cached_session != "bad_session":
        session = {**get_session("geonames"), **{"session_id": cached_session}}
        sessions_cache.save(session["session_id"], session)
    data = {}
    if cached_session:
        data = {**data, **{"session_id": cached_session}}
    response = client.post(
        "/session/continue/cached",
        data=data,
        follow_redirects=False,
    )

    # redirect to annotate page if cached session has been found
    if cached_session != "bad_session" and file_exists:
        assert response.status_code == 302
        assert (
            response.next_request.url
            == f"http://testserver/session/{cached_session}/document/0/annotate"
        )
    # otherwise, always redirect to continue_session
    else:
        assert response.status_code == 302
        assert response.next_request.url == "http://testserver/continue_session"


@pytest.mark.parametrize("file", [True, False])
@pytest.mark.parametrize("session_id", ["", "test_session"])
def test_continue_session_file(client: TestClient, file: bool, session_id: bool):
    files = {}
    if file:
        file_content = {
            "session_id": session_id,
            "created_at": "2024-12-08T20:33:56.472025",
            "last_updated": "2024-12-08T20:41:27.948773",
            "gazetteer": "geonames",
            "settings": {
                "one_sense_per_discourse": False,
                "auto_close_annotation_modal": False,
            },
            "documents": [
                {
                    "filename": "test.txt",
                    "spacy_model": "en_core_web_sm",
                    "text": "Andorra is nice.",
                    "toponyms": [
                        {"text": "Andorra", "start": 0, "end": 7, "loc_id": ""},
                    ],
                }
            ],
        }
        files = {
            "files": [
                (
                    "session_file",
                    (
                        "test.json",
                        io.BytesIO(bytes(json.dumps(file_content), encoding="utf8")),
                    ),
                )
            ]
        }
    response = client.post(
        "/session/continue/file",
        follow_redirects=False,
        **files,
    )
    # redirect to annotate page with known session_id
    if file and session_id:
        assert response.status_code == 302
        assert (
            response.next_request.url
            == f"http://testserver/session/{session_id}/document/0/annotate"
        )
    # redirect to annotate page with new valid session_id
    elif file and not session_id:
        assert response.status_code == 302
        assert re.search(
            r"http:\/\/testserver\/session\/[a-z0-9]{32}\/document\/0\/annotate",
            str(response.next_request.url),
        )
    # otherwise, always redirect to continue_session
    else:
        assert response.status_code == 302
        assert response.next_request.url == "http://testserver/continue_session"


@pytest.mark.parametrize("valid_session", [True, False])
def test_delete_session(client: TestClient, valid_session: bool):
    session_id = "delete_session"
    if valid_session:
        set_session(session_id)
    # call endpoint for first time
    response = client.delete(f"/session/{session_id}")
    if not valid_session:
        # delete fails if there is no session in the first place
        validate_json_response(
            response, 404, {"message": "Session not found.", "status": "error"}
        )
    else:
        # first delete is successful
        validate_json_response(response, 200, {"status": "success"})
        # second delete fails
        second_response = client.delete(f"/session/{session_id}")
        validate_json_response(
            second_response, 404, {"message": "Session not found.", "status": "error"}
        )


@pytest.mark.parametrize("valid_session", [True, False])
@pytest.mark.parametrize("uploaded_files", [True, False])
def test_add_documents(client: TestClient, valid_session: bool, uploaded_files: bool):
    session_id = "add_documents"
    if valid_session:
        set_session(session_id)
    filename = "annotator_doc0.txt"
    files = (
        {
            "files": [
                (
                    "files",
                    (
                        filename,
                        open(get_static_test_file(filename), "rb"),
                    ),
                )
            ]
        }
        if uploaded_files
        else {}
    )
    response = client.post(
        f"/session/{session_id}/documents",
        data={"spacy_model": "en_core_web_sm"},
        follow_redirects=False,
        **files,
    )
    if not valid_session:
        validate_json_response(
            response, 404, {"message": "Session not found.", "status": "error"}
        )
    elif not uploaded_files:
        validate_json_response(
            response,
            422,
            {"message": "No files selected.", "status": "error"},
        )
    else:
        validate_json_response(response, 200, {"status": "success"})


@pytest.mark.parametrize("valid_session", [True, False])
def test_get_documents(client: TestClient, valid_session: bool):
    session_id = "get_documents"
    if valid_session:
        session = set_session(session_id)
    response = client.get(
        f"/session/{session_id}/documents",
    )
    if not valid_session:
        validate_json_response(
            response, 404, {"message": "Session not found.", "status": "error"}
        )
    else:
        validate_json_response(response, 200, session["documents"])


@pytest.mark.parametrize("valid_session", [True, False])
@pytest.mark.parametrize("doc_index", [0, 1])
@pytest.mark.parametrize("spacy_applied", [True, False])
def test_parse_document(
    client: TestClient, valid_session: bool, doc_index: int, spacy_applied: bool
):
    session_id = "parse_document"
    if valid_session:
        set_session(session_id, spacy_applied=spacy_applied)
    response = client.post(
        f"/session/{session_id}/document/{doc_index}/parse",
    )
    if not valid_session:
        validate_json_response(
            response, 404, {"message": "Session not found", "status": "error"}
        )
    elif doc_index == 1:
        validate_json_response(
            response, 422, {"message": "Invalid document index", "status": "error"}
        )
    else:
        validate_json_response(
            response, 200, {"status": "success", "parsed": not spacy_applied}
        )
        # document has been parsed with spacy
        session = sessions_cache.load(session_id)
        assert session["documents"][doc_index]["spacy_applied"] is True


@pytest.mark.parametrize("valid_session", [True, False])
@pytest.mark.parametrize("loc_id", ["", "123"])
def test_get_document_progress(client: TestClient, valid_session: bool, loc_id: str):
    session_id = "get_document_progress"
    toponyms = [{"text": "Andorra", "start": 0, "end": 7, "loc_id": loc_id}]
    if valid_session:
        set_session(session_id, toponyms=toponyms)
    response = client.get(
        f"/session/{session_id}/document/{0}/progress",
    )
    if not valid_session:
        validate_json_response(
            response, 404, {"error": "Session not found", "status": "error"}
        )
    else:
        expected = {
            "status": "success",
            "annotated_toponyms": 0 if not loc_id else 1,
            "total_toponyms": 1,
            "progress_percentage": 0.0 if not loc_id else 100.0,
        }
        validate_json_response(response, 200, expected)


@pytest.mark.parametrize("valid_session", [True, False])
def test_get_document_text(client: TestClient, valid_session: bool):
    session_id = "get_document_text"
    toponyms = [{"text": "Andorra", "start": 0, "end": 7, "loc_id": ""}]
    if valid_session:
        set_session(
            session_id, toponyms=toponyms, text="Andorra is as nice as Andorra."
        )
    response = client.get(
        f"/session/{session_id}/document/{0}/text",
    )
    if not valid_session:
        validate_json_response(
            response, 404, {"error": "Session not found", "status": "error"}
        )
    else:
        expected = {
            "status": "success",
            "pre_annotated_text": '<span class="toponym " data-start="0" data-end="7">Andorra</span> is as nice as Andorra.',
        }
        validate_json_response(response, 200, expected)


@pytest.mark.parametrize("valid_session", [True, False])
@pytest.mark.parametrize("doc_index", [0, 1])
def test_delete_document(client: TestClient, valid_session: bool, doc_index: int):
    session_id = "remove_document"
    if valid_session:
        set_session(session_id)
    response = client.delete(
        f"/session/{session_id}/document/{doc_index}",
    )
    if not valid_session:
        validate_json_response(
            response, 404, {"message": "Session not found.", "status": "error"}
        )
    elif doc_index == 1:
        validate_json_response(
            response, 422, {"message": "Invalid document index.", "status": "error"}
        )
    else:
        validate_json_response(response, 200, {"status": "success"})


@pytest.mark.parametrize("valid_session", [True, False])
@pytest.mark.parametrize("valid_toponym", [True, False])
def test_get_candidates(
    client: TestClient, valid_session: bool, valid_toponym: bool, monkeypatch
):
    monkeypatched_return = {
        "candidates": [{}],
        "existing_candidate": None,
        "existing_loc_id": "123",
        "filter_attributes": [],
    }
    monkeypatch.setattr(
        annotator,
        "get_candidates",
        lambda *args, **kwargs: monkeypatched_return,
    )
    session_id = "get_candidates"
    toponyms = [{"text": "Andorra", "start": 0, "end": 7, "loc_id": ""}]
    if valid_session:
        set_session(session_id, toponyms=toponyms)
    query = {
        "query_text": toponyms[0]["text"],
        "text": toponyms[0]["text"],
        "start": toponyms[0]["start"] if valid_toponym else 99,
        "end": toponyms[0]["end"] if valid_toponym else 100,
    }
    response = client.post(
        f"/session/{session_id}/document/{0}/get_candidates",
        json=query,
    )
    if not valid_session:
        validate_json_response(response, 404, {"error": "Session not found"})
    elif not valid_toponym:
        validate_json_response(response, 404, {"error": "Toponym not found"})
    else:
        validate_json_response(response, 200, monkeypatched_return)


@pytest.mark.parametrize("valid_session", [True, False])
@pytest.mark.parametrize("existing_toponym", [True, False])
def test_create_annotation(
    client: TestClient, valid_session: bool, existing_toponym: bool
):
    session_id = "create_annotation"
    toponyms = [{"text": "Andorra", "start": 0, "end": 7, "loc_id": ""}]
    if valid_session:
        set_session(session_id, toponyms=toponyms)
    data = {
        "session_id": session_id,
        "doc_index": 0,
        "query_text": toponyms[0]["text"],
        "text": toponyms[0]["text"],
        "start": toponyms[0]["start"] if existing_toponym else 22,
        "end": toponyms[0]["end"] if existing_toponym else 29,
    }
    response = client.post(
        f"/session/{session_id}/document/{0}/annotation",
        json=data,
    )
    if not valid_session:
        validate_json_response(response, 404, {"error": "Session not found"})
    elif existing_toponym:
        validate_json_response(response, 422, {"error": "Toponym already exists"})
    else:
        expected = {
            "status": "success",
            "annotated_toponyms": 0,
            "total_toponyms": 2,
            "progress_percentage": 0.0,
        }
        validate_json_response(response, 200, expected)


@pytest.mark.parametrize("valid_session", [True, False])
def test_download_annotations(client: TestClient, valid_session: bool):
    session_id = "download_annotations"
    if valid_session:
        session = set_session(session_id)
    response = client.get(f"/session/{session_id}/annotations/download")
    if not valid_session:
        validate_json_response(response, 404, {"error": "Session not found"})
    else:
        # exact same session is downloaded again
        assert response.status_code == 200
        assert json.loads(response.content.decode("utf8")) == session


@pytest.mark.parametrize("valid_session", [True, False])
@pytest.mark.parametrize("valid_toponym", [True, False])
@pytest.mark.parametrize("one_sense_per_discourse", [True, False])
def test_overwrite_annotation(
    client: TestClient,
    valid_session: bool,
    valid_toponym: bool,
    one_sense_per_discourse: bool,
    radio_andorra_id: int,
):
    session_id = "save_annotation"
    toponyms = [
        {
            "text": "Andorra",
            "start": 0,
            "end": 7,
            "loc_id": "",
        },
        {
            "text": "Andorra",
            "start": 22,
            "end": 29,
            "loc_id": "",
        },
    ]
    if valid_session:
        set_session(
            f"{session_id}-{one_sense_per_discourse}",
            settings={"one_sense_per_discourse": one_sense_per_discourse},
            toponyms=toponyms,
            text="Andorra is as nice as Andorra.",
        )
    data = {
        "start": toponyms[0]["start"] if valid_toponym else 99,
        "end": toponyms[0]["end"] if valid_toponym else 99,
        "loc_id": radio_andorra_id,
    }
    response = client.put(
        f"/session/{session_id}-{one_sense_per_discourse}/document/{0}/annotation",
        json=data,
    )
    if not valid_session:
        validate_json_response(response, 404, {"error": "Session not found"})
    elif not valid_toponym:
        validate_json_response(response, 404, {"error": "Toponym not found"})
    else:
        expected = {
            "status": "success",
            "annotated_toponyms": 1 if not one_sense_per_discourse else 2,
            "total_toponyms": 2,
            "progress_percentage": 50.0 if not one_sense_per_discourse else 100.0,
        }
        validate_json_response(response, 200, expected)


@pytest.mark.parametrize("valid_session", [True, False])
@pytest.mark.parametrize("valid_toponym", [True, False])
def test_update_annotation(
    client: TestClient, valid_session: bool, valid_toponym: bool
):
    session_id = "patch_annotation"
    toponyms = [{"text": "Andorra", "start": 0, "end": 7, "loc_id": "123"}]
    if valid_session:
        set_session(session_id, toponyms=toponyms)
    data = {
        "old_start": toponyms[0]["start"] if valid_toponym else 99,
        "old_end": toponyms[0]["end"] if valid_toponym else 100,
        "new_text": "Andorra la Vella",
        "new_start": 0,
        "new_end": 16,
    }
    response = client.patch(
        f"/session/{session_id}/document/{0}/annotation",
        json=data,
    )
    if not valid_session:
        validate_json_response(response, 404, {"error": "Session not found"})
    elif not valid_toponym:
        validate_json_response(response, 404, {"error": "Toponym not found"})
    else:
        expected = {
            "status": "success",
            "annotated_toponyms": 1,
            "total_toponyms": 1,
            "progress_percentage": 100.0,
        }
        validate_json_response(response, 200, expected)


@pytest.mark.parametrize("valid_session", [True, False])
@pytest.mark.parametrize("valid_toponym", [True, False])
def test_delete_annotation(
    client: TestClient, valid_session: bool, valid_toponym: bool
):
    session_id = "delete_annotation"
    toponyms = [{"text": "Andorra", "start": 0, "end": 7, "loc_id": ""}]
    if valid_session:
        set_session(session_id)
    data = {
        "start": toponyms[0]["start"] if valid_toponym else 99,
        "end": toponyms[0]["end"] if valid_toponym else 100,
    }
    response = client.delete(
        f"/session/{session_id}/document/{0}/annotation",
        params=data,
    )
    if not valid_session:
        validate_json_response(response, 404, {"error": "Session not found"})
    elif not valid_toponym:
        validate_json_response(response, 404, {"error": "Toponym not found"})
    else:
        expected = {
            "status": "success",
            "annotated_toponyms": 0,
            "total_toponyms": 0,
            "progress_percentage": 0.0,
        }
        validate_json_response(response, 200, expected)


@pytest.mark.parametrize("valid_session", [True, False])
def test_get_session_settings(client: TestClient, valid_session: bool):
    session_id = "get_session_settings"
    if valid_session:
        set_session(session_id)
    response = client.get(
        f"/session/{session_id}/settings",
    )
    if not valid_session:
        validate_json_response(
            response, 404, {"status": "error", "error": "Session not found"}
        )
    else:
        validate_json_response(response, 200, get_session("geonames")["settings"])


@pytest.mark.parametrize("valid_session", [True, False])
def test_put_session_settings(client: TestClient, valid_session: bool):
    session_id = "update_settings"
    if valid_session:
        old_settings = {
            "one_sense_per_discourse": False,
            "auto_close_annotation_modal": False,
        }
        set_session(session_id, settings=old_settings)
        # check if old settings are in place
        assert sessions_cache.load(session_id)["settings"] == old_settings
    new_settings = {
        "auto_close_annotation_modal": True,
        "one_sense_per_discourse": True,
    }
    response = client.put(
        f"/session/{session_id}/settings",
        json=new_settings,
    )
    if not valid_session:
        validate_json_response(response, 404, {"error": "Session not found"})
    else:
        validate_json_response(response, 200, {"status": "success"})
        # check if new settings are in place
        assert sessions_cache.load(session_id)["settings"] == new_settings
