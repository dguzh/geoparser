import json
import typing as t
import uuid

import pytest
from fastapi import Depends, FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.testclient import TestClient
from sqlmodel import Session as DBSession

from geoparser.annotator.app import get_db
from geoparser.annotator.exceptions import (
    DocumentNotFoundException,
    SessionNotFoundException,
    SessionSettingsNotFoundException,
    ToponymNotFoundException,
    ToponymOverlapException,
    document_exception_handler,
    session_exception_handler,
    sessionsettings_exception_handler,
    toponym_exception_handler,
    toponym_overlap_exception_handler,
)
from geoparser.annotator.models.api import BaseResponse
from geoparser.db.crud import (
    DocumentRepository,
    SessionRepository,
    SessionSettingsRepository,
    ToponymRepository,
)
from geoparser.db.models import DocumentCreate, SessionCreate, ToponymCreate

app = FastAPI()
app.add_exception_handler(SessionNotFoundException, session_exception_handler)
app.add_exception_handler(
    SessionSettingsNotFoundException, sessionsettings_exception_handler
)
app.add_exception_handler(DocumentNotFoundException, document_exception_handler)
app.add_exception_handler(ToponymNotFoundException, toponym_exception_handler)
app.add_exception_handler(ToponymOverlapException, toponym_overlap_exception_handler)


@pytest.fixture()
def client(test_db: DBSession) -> t.Iterator[TestClient]:
    def get_db_override():
        return test_db

    app.dependency_overrides[get_db] = get_db_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@app.get("/get/{db_object}/{id}")
def get_object(
    db: t.Annotated[DBSession, Depends(get_db)], db_object: str, id: uuid.UUID
):
    object_mapping = {
        "session": SessionRepository,
        "settings": SessionSettingsRepository,
        "document": DocumentRepository,
        "toponym": ToponymRepository,
    }
    return object_mapping[db_object].read(db, id)


@app.get("/get/{db_object}/{id}")
def get_object(
    db: t.Annotated[DBSession, Depends(get_db)], db_object: str, id: uuid.UUID
):
    object_mapping = {
        "session": SessionRepository,
        "settings": SessionSettingsRepository,
        "document": DocumentRepository,
        "toponym": ToponymRepository,
    }
    # will always fail because id is invalid in test case below
    return object_mapping[db_object].read(db, id)


@app.get("/toponym/create_twice")
def create_toponym_twice(db: t.Annotated[DBSession, Depends(get_db)]):
    # setup: create session and document to link toponym to
    session = SessionRepository.create(
        db,
        SessionCreate(
            gazetteer="geonames",
            documents=[
                DocumentCreate(
                    filename="test.txt", spacy_model="en_core_web_sm", text="test"
                )
            ],
        ),
    )
    toponym = ToponymCreate(text="Andorra", start=0, end=6)
    # works
    ToponymRepository.create(
        db, toponym, additional={"document_id": session.documents[0].id}
    )
    # throws ToponymOverlapException (handled by exception handler)
    ToponymRepository.create(
        db, toponym, additional={"document_id": session.documents[0].id}
    )


@pytest.mark.parametrize(
    "object,status_code,expected_json",
    [
        (
            "session",
            404,
            jsonable_encoder(
                BaseResponse(status="error", message="Session not found.")
            ),
        ),
        (
            "settings",
            404,
            jsonable_encoder(
                BaseResponse(status="error", message="Settings not found.")
            ),
        ),
        (
            "document",
            422,
            jsonable_encoder(
                BaseResponse(status="error", message="Invalid document index.")
            ),
        ),
        (
            "toponym",
            404,
            jsonable_encoder(
                BaseResponse(status="error", message="Toponym not found.")
            ),
        ),
    ],
)
def test_provoke_not_found_exception(
    client: TestClient, object: str, status_code: int, expected_json: dict
):
    response = client.get(f"/get/{object}/{uuid.uuid4()}")
    assert response.status_code == status_code
    assert json.loads(response.content.decode("utf-8")) == expected_json


def test_provoke_toponym_overlap(client: TestClient):
    response = client.get("/toponym/create_twice")
    expected_json = jsonable_encoder(
        BaseResponse(status="error", message="Overlap with existing toponym.")
    )
    assert response.status_code == 422
    assert json.loads(response.content.decode("utf-8")) == expected_json


# test toponym overlap
