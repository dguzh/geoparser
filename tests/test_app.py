import io
import json
import tempfile
import time
import typing as t
import uuid
from contextlib import contextmanager
from datetime import datetime

import py
import pytest
from flask import template_rendered
from flask.testing import FlaskClient
from jinja2.environment import Template
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
    return app.test_client()


@contextmanager
def captured_templates(app):
    recorded = []

    def record(sender, template, context, **extra):
        recorded.append((template, context))

    template_rendered.connect(record, app)
    try:
        yield recorded
    finally:
        template_rendered.disconnect(record, app)


def get_first_template(
    templates: list[tuple[Template, dict[str, str]]]
) -> t.Optional[Template]:
    if len(templates) >= 1:
        template, _ = templates[0]
        return template


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
            in response.data
        )


def set_session(session_id: str, *, settings=None, **document_kwargs) -> dict:
    session = {
        **get_session("geonames"),
        **{
            "session_id": session_id,
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


def test_index(client: FlaskClient):
    with captured_templates(app) as templates:
        response = client.get("/")
        template = get_first_template(templates)
    assert response.status_code == 200
    # index.html has been used
    assert len(templates) == 1
    assert template.name == "index.html"
    # no errors: returns index html template
    assert b"<title>Geoparser Annotator</title>" in response.data


def test_start_new_session_get(client: FlaskClient):
    with captured_templates(app) as templates:
        response = client.get("/start_new_session")
        template = get_first_template(templates)
    assert response.status_code == 200
    # start_new_session.html has been used
    assert len(templates) == 1
    assert template.name == "start_new_session.html"
    # no errors: returns start_new_session html template
    assert b"<title>Start New Session</title>" in response.data


def test_post_session(client: FlaskClient):
    filename = "annotator_doc0.txt"
    response = client.post(
        "/session",
        data={
            "gazetteer": "geonames",
            "spacy_model": "en_core_web_sm",
            "files[]": [(open(get_static_test_file(filename), "rb"), filename)],
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 302
    # redirected to annotate page for first document
    assert b"/annotate/" in response.data
    assert b"?doc_index=0" in response.data


def test_continue_session_get(client: FlaskClient):
    with captured_templates(app) as templates:
        response = client.get("/continue_session")
        template = get_first_template(templates)
    assert response.status_code == 200
    # index.html has been used
    assert len(templates) == 1
    assert template.name == "continue_session.html"
    # no errors: returns continue_session html template
    assert b"<title>Continue Session</title>" in response.data


@pytest.mark.parametrize("cached_session", [None, "test_load_cached"])
@pytest.mark.parametrize("file_exists", [True, False])
def test_continue_session_cached(
    client: FlaskClient, cached_session: str, file_exists: bool, monkeypatch
):
    if file_exists and cached_session:
        session = {**get_session("geonames"), **{"session_id": cached_session}}
        sessions_cache.save(session["session_id"], session)
    data = {}
    if cached_session:
        data = {**data, **{"cached_session": cached_session}}
    response = client.post(
        "/session/continue/cached",
        data=data,
        content_type="multipart/form-data",
    )

    # redirect to annotate page if cached session has been found
    if cached_session and file_exists:
        assert response.status_code == 302
        assert (
            b'<a href="/annotate/test_load_cached?doc_index=0">/annotate/test_load_cached?doc_index=0</a>'
            in response.data
        )
    # otherwise, always redirect to continue_session
    else:
        assert response.status_code == 302
        assert b'<a href="/continue_session">/continue_session</a>' in response.data


@pytest.mark.parametrize("file", [True, False])
@pytest.mark.parametrize("session_id", ["", "test_session"])
def test_continue_session_file(client: FlaskClient, file: bool, session_id: bool):
    data = {"action": "load_file"}
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
        data = {
            **data,
            **{
                "session_file": (
                    io.BytesIO(bytes(json.dumps(file_content), encoding="utf8")),
                    "test.json",
                )
            },
        }
    response = client.post(
        "/session/continue/file",
        data=data,
        content_type="multipart/form-data",
    )
    # redirect to annotate page if file can be read
    if file:
        assert response.status_code == 302
        assert b"/annotate/" in response.data
        assert b"?doc_index=0" in response.data
    # otherwise, always redirect to continue_session
    else:
        assert response.status_code == 302
        assert b'<a href="/continue_session">/continue_session</a>' in response.data


@pytest.mark.parametrize("valid_session", [True, False])
@pytest.mark.parametrize("doc_index", [0, 1])
def test_annotate(client: FlaskClient, valid_session: bool, doc_index: int):
    session_id = "annotate"
    if valid_session:
        set_session(session_id)
    with captured_templates(app) as templates:
        response = client.get(
            f"/annotate/{session_id}", query_string={"doc_index": doc_index}
        )
        template = get_first_template(templates)
    # redirect to index if session is invalid
    if not valid_session:
        assert response.status_code == 302
        assert b'<a href="/">/</a>' in response.data
    # invalid doc_index always redirects to 0
    elif valid_session and doc_index == 1:
        assert response.status_code == 302
        assert (
            b' <a href="/annotate/annotate?doc_index=0">/annotate/annotate?doc_index=0</a>'
            in response.data
        )
    # vaild doc_index returns the annotate page
    elif valid_session and doc_index == 0:
        assert response.status_code == 200
        assert template.name == "annotate.html"


@pytest.mark.parametrize("valid_session", [True, False])
@pytest.mark.parametrize("valid_toponym", [True, False])
def test_get_candidates(
    client: FlaskClient, valid_session: bool, valid_toponym: bool, monkeypatch
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
    params = {
        "query_text": toponyms[0]["text"],
        "text": toponyms[0]["text"],
        "start": toponyms[0]["start"] if valid_toponym else 99,
        "end": toponyms[0]["end"] if valid_toponym else 100,
    }
    response = client.get(
        f"/session/{session_id}/document/{0}/candidates",
        query_string=params,
        content_type="application/json",
    )
    if not valid_session:
        validate_json_response(response, 404, {"error": "Session not found"})
    elif not valid_toponym:
        validate_json_response(response, 404, {"error": "Toponym not found"})
    else:
        validate_json_response(response, 200, monkeypatched_return)


@pytest.mark.parametrize("valid_session", [True, False])
@pytest.mark.parametrize("valid_toponym", [True, False])
@pytest.mark.parametrize("one_sense_per_discourse", [True, False])
def test_save_annotation(
    client: FlaskClient,
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
        "session_id": f"{session_id}-{one_sense_per_discourse}",
        "doc_index": 0,
        "annotation": {
            "start": toponyms[0]["start"] if valid_toponym else 99,
            "end": toponyms[0]["end"] if valid_toponym else 99,
            "loc_id": radio_andorra_id,
        },
    }
    response = client.post(
        "/save_annotation",
        json=data,
        content_type="application/json",
    )
    if not valid_session:
        validate_json_response(response, 404, {"error": "Session not found"})
    elif not valid_toponym:
        validate_json_response(response, 404, {"error": "Toponym not found"})
    else:
        expected = {
            "annotated_toponyms": 1 if not one_sense_per_discourse else 2,
            "progress_percentage": 50.0 if not one_sense_per_discourse else 100.0,
            "status": "success",
            "total_toponyms": 2,
        }
        validate_json_response(response, 200, expected)


@pytest.mark.parametrize("valid_session", [True, False])
def test_download_annotations(client: FlaskClient, valid_session: bool):
    session_id = "download_annotations"
    if valid_session:
        session = set_session(session_id)
    response = client.get(f"/download_annotations/{session_id}")
    if not valid_session:
        assert response.status_code == 404
        assert b"Session not found" in response.data
    else:
        # exact same session is downloaded again
        assert response.status_code == 200
        assert json.loads(response.data.decode("utf8")) == session
        # wait for file to be deleted
        time.sleep(1.001)


@pytest.mark.parametrize("valid_session", [True, False])
def test_delete_session(client: FlaskClient, valid_session: bool):
    session_id = "delete_session"
    if valid_session:
        set_session(session_id)
    # call endpoint for first time
    response = client.delete(f"/session/{session_id}")
    if not valid_session:
        # delete fails if there is no session in the first place
        validate_json_response(
            response, 200, {"message": "Session not found.", "status": "error"}
        )
    else:
        # first delete is successful
        validate_json_response(response, 200, {"status": "success"})
        # second delete fails
        second_response = client.delete(f"/session/{session_id}")
        validate_json_response(
            second_response, 200, {"message": "Session not found.", "status": "error"}
        )


@pytest.mark.parametrize("valid_session", [True, False])
@pytest.mark.parametrize("uploaded_files", [True, False])
@pytest.mark.parametrize("spacy_model", [True, False])
def test_add_documents(
    client: FlaskClient, valid_session: bool, uploaded_files: bool, spacy_model: bool
):
    session_id = "add_documents"
    if valid_session:
        set_session(session_id)
    filename = "annotator_doc0.txt"
    files = (
        {"files[]": [(open(get_static_test_file(filename), "rb"), filename)]}
        if uploaded_files
        else {}
    )
    model = {"spacy_model": "en_core_web_sm"} if spacy_model else {}
    response = client.post(
        "/add_documents",
        data={"gazetteer": "geonames", "session_id": session_id, **files, **model},
        content_type="multipart/form-data",
    )
    if not valid_session:
        validate_json_response(
            response, 200, {"message": "Session not found.", "status": "error"}
        )
    elif not uploaded_files or not spacy_model:
        validate_json_response(
            response,
            200,
            {"message": "No files or SpaCy model selected.", "status": "error"},
        )
    else:
        validate_json_response(response, 200, {"status": "success"})


@pytest.mark.parametrize("valid_session", [True, False])
@pytest.mark.parametrize("doc_index", [0, 1])
def test_remove_document(client: FlaskClient, valid_session: bool, doc_index: int):
    session_id = "remove_document"
    if valid_session:
        set_session(session_id)
    response = client.post(
        "/remove_document",
        json={"session_id": session_id, "doc_index": doc_index},
        content_type="application/json",
    )
    if not valid_session:
        validate_json_response(
            response, 200, {"message": "Session not found.", "status": "error"}
        )
    elif doc_index == 1:
        validate_json_response(
            response, 200, {"message": "Invalid document index.", "status": "error"}
        )
    else:
        validate_json_response(response, 200, {"status": "success"})


@pytest.mark.parametrize("valid_session", [True, False])
@pytest.mark.parametrize("valid_toponym", [True, False])
def test_delete_annotation(
    client: FlaskClient, valid_session: bool, valid_toponym: bool
):
    session_id = "delete_annotation"
    toponyms = [{"text": "Andorra", "start": 0, "end": 7, "loc_id": ""}]
    if valid_session:
        set_session(session_id)
    data = {
        "session_id": session_id,
        "doc_index": 0,
        "query_text": toponyms[0]["text"],
        "text": toponyms[0]["text"],
        "start": toponyms[0]["start"] if valid_toponym else 99,
        "end": toponyms[0]["end"] if valid_toponym else 100,
    }
    response = client.post(
        "/delete_annotation",
        json=data,
        content_type="application/json",
    )
    if not valid_session:
        validate_json_response(response, 404, {"error": "Session not found"})
    elif not valid_toponym:
        validate_json_response(response, 404, {"error": "Toponym not found"})
    else:
        expected = {
            "annotated_toponyms": 0,
            "progress_percentage": 0.0,
            "status": "success",
            "total_toponyms": 0,
        }
        validate_json_response(response, 200, expected)


@pytest.mark.parametrize("valid_session", [True, False])
@pytest.mark.parametrize("valid_toponym", [True, False])
def test_edit_annotation(client: FlaskClient, valid_session: bool, valid_toponym: bool):
    session_id = "delete_annotation"
    toponyms = [{"text": "Andorra", "start": 0, "end": 7, "loc_id": "123"}]
    if valid_session:
        set_session(session_id, toponyms=toponyms)
    data = {
        "session_id": session_id,
        "doc_index": 0,
        "old_start": toponyms[0]["start"] if valid_toponym else 99,
        "old_end": toponyms[0]["end"] if valid_toponym else 100,
        "new_text": "Andorra la Vella",
        "new_start": 0,
        "new_end": 16,
    }
    response = client.post(
        "/edit_annotation",
        json=data,
        content_type="application/json",
    )
    if not valid_session:
        validate_json_response(response, 404, {"error": "Session not found"})
    elif not valid_toponym:
        validate_json_response(response, 404, {"error": "Toponym not found"})
    else:
        expected = {
            "annotated_toponyms": 1,
            "progress_percentage": 100.0,
            "status": "success",
            "total_toponyms": 1,
        }
        validate_json_response(response, 200, expected)


@pytest.mark.parametrize("valid_session", [True, False])
@pytest.mark.parametrize("existing_toponym", [True, False])
def test_create_annotation(
    client: FlaskClient, valid_session: bool, existing_toponym: bool
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
        "/create_annotation",
        json=data,
        content_type="application/json",
    )
    if not valid_session:
        validate_json_response(response, 404, {"error": "Session not found"})
    elif existing_toponym:
        validate_json_response(response, 400, {"error": "Toponym already exists"})
    else:
        expected = {
            "annotated_toponyms": 0,
            "progress_percentage": 0.0,
            "status": "success",
            "total_toponyms": 2,
        }
        validate_json_response(response, 200, expected)


@pytest.mark.parametrize("valid_session", [True, False])
def test_get_document_text(client: FlaskClient, valid_session: bool):
    session_id = "get_document_text"
    toponyms = [{"text": "Andorra", "start": 0, "end": 7, "loc_id": ""}]
    if valid_session:
        set_session(
            session_id, toponyms=toponyms, text="Andorra is as nice as Andorra."
        )
    data = {
        "session_id": session_id,
        "doc_index": 0,
    }
    response = client.post(
        "/get_document_text",
        json=data,
        content_type="application/json",
    )
    if not valid_session:
        validate_json_response(
            response, 404, {"error": "Session not found", "status": "error"}
        )
    else:
        expected = {
            "pre_annotated_text": '<span class="toponym " data-start="0" data-end="7">Andorra</span> is as nice as Andorra.',
            "status": "success",
        }
        validate_json_response(response, 200, expected)


@pytest.mark.parametrize("valid_session", [True, False])
@pytest.mark.parametrize("loc_id", ["", "123"])
def test_get_document_progress(client: FlaskClient, valid_session: bool, loc_id: str):
    session_id = "get_document_progress"
    toponyms = [{"text": "Andorra", "start": 0, "end": 7, "loc_id": loc_id}]
    if valid_session:
        set_session(session_id, toponyms=toponyms)
    data = {
        "session_id": session_id,
        "doc_index": 0,
    }
    response = client.post(
        "/get_document_progress",
        json=data,
        content_type="application/json",
    )
    if not valid_session:
        validate_json_response(
            response, 404, {"error": "Session not found", "status": "error"}
        )
    else:
        expected = {
            "annotated_toponyms": 0 if not loc_id else 1,
            "progress_percentage": 0.0 if not loc_id else 100.0,
            "status": "success",
            "total_toponyms": 1,
        }
        validate_json_response(response, 200, expected)


@pytest.mark.parametrize("valid_session", [True, False])
def test_get_session_settings(client: FlaskClient, valid_session: bool):
    session_id = "get_session_settings"
    if valid_session:
        set_session(session_id)
    response = client.get(
        f"/session/{session_id}/settings",
        content_type="application/json",
    )
    if not valid_session:
        validate_json_response(
            response, 404, {"error": "Session not found", "status": "error"}
        )
    else:
        validate_json_response(response, 200, get_session("geonames")["settings"])


@pytest.mark.parametrize("valid_session", [True, False])
def test_put_session_settings(client: FlaskClient, valid_session: bool):
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
        content_type="application/json",
    )
    if not valid_session:
        validate_json_response(response, 404, {"error": "Session not found"})
    else:
        validate_json_response(response, 200, {"status": "success"})
        # check if new settings are in place
        assert sessions_cache.load(session_id)["settings"] == new_settings