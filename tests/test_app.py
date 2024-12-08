import io
import json
import tempfile
import typing as t
import uuid
from contextlib import contextmanager
from datetime import datetime

import py
import pytest
from flask import template_rendered
from flask.testing import FlaskClient
from jinja2.environment import Template

from geoparser.annotator.app import app, get_session, sessions_cache
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
    # index.html has been used
    assert len(templates) == 1
    assert template.name == "index.html"
    # no errors: returns index html template
    assert b"<title>Geoparser Annotator</title>" in response.data


def test_start_new_session_get(client: FlaskClient):
    with captured_templates(app) as templates:
        response = client.get("/start_new_session")
        template = get_first_template(templates)
    # start_new_session.html has been used
    assert len(templates) == 1
    assert template.name == "start_new_session.html"
    # no errors: returns start_new_session html template
    assert b"<title>Start New Session</title>" in response.data


def test_start_new_session_post(client: FlaskClient):
    filename = "annotator_doc0.txt"
    response = client.post(
        "/start_new_session",
        data={
            "gazetteer": "geonames",
            "spacy_model": "en_core_web_sm",
            "files[]": [(open(get_static_test_file(filename), "rb"), filename)],
        },
        content_type="multipart/form-data",
    )
    # redirected to annotate page for first document
    assert b"/annotate/" in response.data
    assert b"?doc_index=0" in response.data


def test_continue_session_get(client: FlaskClient):
    with captured_templates(app) as templates:
        response = client.get("/continue_session")
        template = get_first_template(templates)
    # index.html has been used
    assert len(templates) == 1
    assert template.name == "continue_session.html"
    # no errors: returns continue_session html template
    assert b"<title>Continue Session</title>" in response.data


@pytest.mark.parametrize("cached_session", [None, "test_load_cached"])
@pytest.mark.parametrize("file_exists", [True, False])
def test_continue_session_post_load_cached(
    client: FlaskClient, cached_session: str, file_exists: bool, monkeypatch
):
    if file_exists and cached_session:
        session = {**get_session("geonames"), **{"session_id": cached_session}}
        sessions_cache.save(session["session_id"], session)
    data = {"action": "load_cached"}
    if cached_session:
        data = {**data, **{"cached_session": cached_session}}
    response = client.post(
        "/continue_session",
        data=data,
        content_type="multipart/form-data",
    )

    # redirect to annotate page if cached session has been found
    if cached_session and file_exists:
        assert (
            b'<a href="/annotate/test_load_cached?doc_index=0">/annotate/test_load_cached?doc_index=0</a>'
            in response.data
        )
    # otherwise, always redirect to continue_session
    else:
        assert b'<a href="/continue_session">/continue_session</a>' in response.data


@pytest.mark.parametrize("file", [True, False])
@pytest.mark.parametrize("session_id", ["", "test_session"])
def test_continue_session_post_load_file(
    client: FlaskClient, file: bool, session_id: bool
):
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
        "/continue_session",
        data=data,
        content_type="multipart/form-data",
    )
    # redirect to annotate page if file can be read
    if file:
        assert b"/annotate/" in response.data
        assert b"?doc_index=0" in response.data
    # otherwise, always redirect to continue_session
    else:
        assert b'<a href="/continue_session">/continue_session</a>' in response.data


def test_continue_session_post_bad_action(client: FlaskClient):
    # bad action always redirects to continue_session
    data = {"action": "bad_action"}
    response = client.post(
        "/continue_session",
        data=data,
        content_type="multipart/form-data",
    )
    assert b'<a href="/continue_session">/continue_session</a>' in response.data


@pytest.mark.parametrize("valid_session", [True, False])
@pytest.mark.parametrize("doc_index", [0, 1])
def test_annotate(client: FlaskClient, valid_session: bool, doc_index: int):
    session_id = "annotate"
    if valid_session:
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
        sessions_cache.save(session["session_id"], session)
    with captured_templates(app) as templates:
        response = client.get(
            f"/annotate/{session_id}", query_string={"doc_index": doc_index}
        )
        template = get_first_template(templates)
    # redirect to index if session is invalid
    if not valid_session:
        assert b'<a href="/">/</a>' in response.data
    # invalid doc_index always redirects to 0
    elif valid_session and doc_index == 1:
        assert (
            b' <a href="/annotate/annotate?doc_index=0">/annotate/annotate?doc_index=0</a>'
            in response.data
        )
    # vaild doc_index returns the annotate page
    elif valid_session and doc_index == 0:
        assert template.name == "annotate.html"
