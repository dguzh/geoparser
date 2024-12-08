import uuid
from datetime import datetime

import pytest
from flask.testing import FlaskClient

from geoparser.annotator.app import app, get_session
from geoparser.constants import DEFAULT_SESSION_SETTINGS


@pytest.fixture(scope="session")
def client():
    return app.test_client()


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
    response = client.get("/")
    # returns html template of title page
    assert b"<title>Geoparser Annotator</title>" in response.data


def test_start_new_session_get(client: FlaskClient):
    response = client.get("/start_new_session")
    # returns html template of new session page
    assert b"<title>Start New Session</title>" in response.data


def test_start_new_session_post(client: FlaskClient):
    response = client.post("/start_new_session")
    pass
