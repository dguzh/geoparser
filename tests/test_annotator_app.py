import io
import json
import re
import typing as t
import uuid

import pytest
from fastapi.encoders import jsonable_encoder
from fastapi.testclient import TestClient
from sqlmodel import Session as DBSession
from werkzeug.wrappers import Response

from geoparser.annotator.app import app, get_db
from geoparser.db.crud import (
    SessionRepository,
    SessionSettingsRepository,
    ToponymRepository,
)
from geoparser.db.models import (
    DocumentCreate,
    Session,
    SessionCreate,
    SessionSettingsCreate,
    ToponymCreate,
)
from geoparser.annotator.models.api import (
    BaseResponse,
    CandidatesGet,
    ParsingResponse,
    PreAnnotatedTextResponse,
    ProgressResponse,
)
from tests.utils import get_static_test_file


@pytest.fixture()
def client(test_db: DBSession) -> t.Iterator[TestClient]:
    def get_db_override():
        return test_db

    app.dependency_overrides[get_db] = get_db_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def set_session(db: DBSession, *, settings: dict = None, **document_kwargs) -> Session:
    session_obj = SessionCreate(
        gazetteer="geonames",
        documents=[
            DocumentCreate(
                filename="test.txt",
                spacy_model="en_core_web_sm",
                text="Andorra is nice.",
                toponyms=[ToponymCreate(text="Andorra", start=0, end=7)],
            )
        ],
    )
    if settings:
        session_obj.settings = settings
    for key, value in document_kwargs.items():
        setattr(session_obj.documents[0], key, value)
    session = SessionRepository.create(db, session_obj)
    return session


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
def test_annotate(
    test_db: DBSession, client: TestClient, valid_session: bool, doc_index: int
):
    session_id = uuid.uuid4()
    if valid_session:
        session = set_session(test_db)
        session_id = session.id
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
        assert re.search(
            r"http:\/\/testserver\/session\/.*\/document\/0\/annotate",
            str(response.next_request.url),
        )
    # vaild doc_index returns the annotate page
    elif valid_session and doc_index == 0:
        assert response.status_code == 200


def test_create_session(client: TestClient):
    filename = "annotator/annotator_doc0.txt"
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


@pytest.mark.parametrize("valid_session", [True, False])
def test_continue_session_cached(
    test_db: DBSession, client: TestClient, valid_session: bool
):
    session_id = uuid.uuid4()
    if valid_session:
        session = set_session(test_db)
        session_id = session.id
    data = {"session_id": session_id}
    response = client.post(
        "/session/continue/cached",
        data=data,
        follow_redirects=False,
    )
    # redirect to annotate page if cached session has been found
    if valid_session:
        assert response.status_code == 302
        assert (
            response.next_request.url
            == f"http://testserver/session/{session_id}/document/0/annotate"
        )
    # otherwise, always redirect to continue_session
    else:
        assert response.status_code == 302
        assert response.next_request.url == "http://testserver/continue_session"


@pytest.mark.parametrize("file", [True, False])
def test_continue_session_file(client: TestClient, file: bool):
    files = {}
    if file:
        file_content = {
            "created_at": "2024-12-08T20:33:56.472025",
            "last_updated": "2024-12-08T20:41:27.948773",
            "gazetteer": "geonames",
            "documents": [
                {
                    "filename": "test.txt",
                    "spacy_model": "en_core_web_sm",
                    "text": "Andorra is nice.",
                    "doc_id": 0,
                    "toponyms": [
                        ToponymCreate(text="Andorra", start=0, end=7),
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
                        io.BytesIO(
                            bytes(
                                json.dumps(jsonable_encoder(file_content)),
                                encoding="utf8",
                            )
                        ),
                    ),
                )
            ]
        }
    response = client.post(
        "/session/continue/file",
        follow_redirects=False,
        **files,
    )
    if file:
        assert response.status_code == 302
        assert re.search(
            r"http:\/\/testserver\/session\/.*\/document\/0\/annotate",
            str(response.next_request.url),
        )
    # otherwise, always redirect to continue_session
    else:
        assert response.status_code == 302
        assert response.next_request.url == "http://testserver/continue_session"


@pytest.mark.parametrize("valid_session", [True, False])
def test_delete_session(test_db: DBSession, client: TestClient, valid_session: bool):
    session_id = uuid.uuid4()
    if valid_session:
        session = set_session(test_db)
        session_id = session.id
    # call endpoint for first time
    response = client.delete(f"/session/{session_id}")
    if not valid_session:
        # delete fails if there is no session in the first place
        validate_json_response(
            response,
            404,
            BaseResponse(status="error", message="Session not found.").model_dump(),
        )
    else:
        # first delete is successful
        validate_json_response(response, 200, BaseResponse().model_dump())
        # second delete fails
        second_response = client.delete(f"/session/{session_id}")
        validate_json_response(
            second_response,
            404,
            BaseResponse(status="error", message="Session not found.").model_dump(),
        )


@pytest.mark.parametrize("valid_session", [True, False])
@pytest.mark.parametrize("uploaded_files", [True, False])
def test_add_documents(
    test_db: DBSession, client: TestClient, valid_session: bool, uploaded_files: bool
):
    session_id = uuid.uuid4()
    if valid_session:
        session = set_session(test_db)
        session_id = session.id
    filename = "annotator/annotator_doc0.txt"
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
            response,
            404,
            BaseResponse(status="error", message="Session not found.").model_dump(),
        )
    elif not uploaded_files:
        validate_json_response(
            response,
            422,
            BaseResponse(status="error", message="No files selected.").model_dump(),
        )
    else:
        validate_json_response(response, 200, BaseResponse().model_dump())


@pytest.mark.parametrize("valid_session", [True, False])
def test_get_documents(test_db: DBSession, client: TestClient, valid_session: bool):
    session_id = uuid.uuid4()
    if valid_session:
        session = set_session(test_db)
        session_id = session.id
    response = client.get(
        f"/session/{session_id}/documents",
    )
    if not valid_session:
        validate_json_response(
            response,
            404,
            BaseResponse(status="error", message="Session not found.").model_dump(),
        )
    else:
        validate_json_response(
            response,
            200,
            [jsonable_encoder(document) for document in session.documents],
        )


@pytest.mark.parametrize("valid_session", [True, False])
@pytest.mark.parametrize("doc_index", [0, 1])
@pytest.mark.parametrize("spacy_applied", [True, False])
def test_parse_document(
    test_db: DBSession,
    client: TestClient,
    valid_session: bool,
    doc_index: int,
    spacy_applied: bool,
):
    session_id = uuid.uuid4()
    if valid_session:
        session = set_session(test_db, spacy_applied=spacy_applied)
        session_id = session.id
    response = client.post(
        f"/session/{session_id}/document/{doc_index}/parse",
    )
    if not valid_session:
        validate_json_response(
            response,
            404,
            BaseResponse(status="error", message="Session not found.").model_dump(),
        )
    elif doc_index == 1:
        validate_json_response(
            response,
            422,
            BaseResponse(
                status="error", message="Invalid document index."
            ).model_dump(),
        )
    else:
        validate_json_response(
            response, 200, ParsingResponse(parsed=not spacy_applied).model_dump()
        )
        # document has been parsed with spacy
        document = SessionRepository.read(test_db, session.id).documents[0]
        assert document.spacy_applied is True


@pytest.mark.parametrize("valid_session", [True, False])
@pytest.mark.parametrize("loc_id", ["", "123"])
def test_get_document_progress(
    test_db: DBSession, client: TestClient, valid_session: bool, loc_id: str
):
    session_id = uuid.uuid4()
    toponyms = [ToponymCreate(text="Andorra", start=0, end=7, loc_id=loc_id)]
    if valid_session:
        session = set_session(test_db, toponyms=toponyms)
        session_id = session.id
    response = client.get(
        f"/session/{session_id}/document/{0}/progress",
    )
    if not valid_session:
        validate_json_response(
            response,
            404,
            BaseResponse(status="error", message="Session not found.").model_dump(),
        )
    else:
        expected = ProgressResponse(
            annotated_toponyms=0 if not loc_id else 1,
            total_toponyms=1,
            progress_percentage=0.0 if not loc_id else 100.0,
            filename="test.txt",
            doc_index=0,
            doc_id=session.documents[0].id,
        )
        validate_json_response(response, 200, jsonable_encoder(expected))


@pytest.mark.parametrize("valid_session", [True, False])
def test_get_document_text(test_db: DBSession, client: TestClient, valid_session: bool):
    session_id = uuid.uuid4()
    toponyms = [ToponymCreate(text="Andorra", start=0, end=7)]
    if valid_session:
        session = set_session(
            test_db, toponyms=toponyms, text="Andorra is as nice as Andorra."
        )
        session_id = session.id
    response = client.get(
        f"/session/{session_id}/document/{0}/text",
    )
    if not valid_session:
        validate_json_response(
            response,
            404,
            BaseResponse(status="error", message="Session not found.").model_dump(),
        )
    else:
        expected = PreAnnotatedTextResponse(
            pre_annotated_text='<span class="toponym " data-start="0" data-end="7">Andorra</span> is as nice as Andorra.'
        ).model_dump()
        validate_json_response(response, 200, expected)


@pytest.mark.parametrize("valid_session", [True, False])
@pytest.mark.parametrize("doc_index", [0, 1])
def test_delete_document(
    test_db: DBSession, client: TestClient, valid_session: bool, doc_index: int
):
    session_id = uuid.uuid4()
    if valid_session:
        session = set_session(test_db)
        session_id = session.id
    response = client.delete(
        f"/session/{session_id}/document/{doc_index}",
    )
    if not valid_session:
        validate_json_response(
            response,
            404,
            BaseResponse(status="error", message="Session not found.").model_dump(),
        )
    elif doc_index == 1:
        validate_json_response(
            response,
            422,
            BaseResponse(
                status="error", message="Invalid document index."
            ).model_dump(),
        )
    else:
        validate_json_response(response, 200, BaseResponse().model_dump())


@pytest.mark.parametrize("valid_session", [True, False])
def test_get_candidates(
    test_db: DBSession,
    client: TestClient,
    valid_session: bool,
    monkeypatch,
):
    monkeypatched_return = {
        "candidates": [{}],
        "existing_candidate": None,
        "existing_loc_id": "123",
        "filter_attributes": [],
    }
    monkeypatch.setattr(
        ToponymRepository,
        "get_candidates",
        lambda *args, **kwargs: monkeypatched_return,
    )
    session_id = uuid.uuid4()
    toponyms = [ToponymCreate(text="Andorra", start=0, end=7)]
    if valid_session:
        session = set_session(test_db, toponyms=toponyms)
        session_id = session.id
    query = CandidatesGet(
        query_text=toponyms[0].text,
        text=toponyms[0].text,
        start=toponyms[0].start,
        end=toponyms[0].end,
    )
    response = client.post(
        f"/session/{session_id}/document/{0}/get_candidates",
        json=jsonable_encoder(query),
    )
    if not valid_session:
        validate_json_response(
            response,
            404,
            BaseResponse(status="error", message="Session not found.").model_dump(),
        )
    else:
        validate_json_response(response, 200, monkeypatched_return)


@pytest.mark.parametrize("valid_session", [True, False])
@pytest.mark.parametrize("existing_toponym", [True, False])
def test_create_annotation(
    test_db: DBSession, client: TestClient, valid_session: bool, existing_toponym: bool
):
    session_id = uuid.uuid4()
    toponyms = [ToponymCreate(text="Andorra", start=0, end=7)]
    if valid_session:
        session = set_session(test_db, toponyms=toponyms)
        session_id = session.id
    data = {
        "session_id": session_id,
        "doc_index": 0,
        "query_text": toponyms[0].text,
        "text": toponyms[0].text,
        "start": toponyms[0].start if existing_toponym else 22,
        "end": toponyms[0].end if existing_toponym else 29,
    }
    response = client.post(
        f"/session/{session_id}/document/{0}/annotation",
        json=jsonable_encoder(data),
    )
    if not valid_session:
        validate_json_response(
            response,
            404,
            BaseResponse(status="error", message="Session not found.").model_dump(),
        )
    elif existing_toponym:
        validate_json_response(
            response,
            422,
            BaseResponse(
                status="error", message="Overlap with existing toponym."
            ).model_dump(),
        )
    else:
        expected = BaseResponse().model_dump()
        validate_json_response(response, 200, jsonable_encoder(expected))


@pytest.mark.parametrize("valid_session", [True, False])
def test_download_annotations(
    test_db: DBSession, client: TestClient, valid_session: bool
):
    session_id = uuid.uuid4()
    if valid_session:
        session = set_session(test_db)
        session_id = session.id
    response = client.get(f"/session/{session_id}/annotations/download")
    if not valid_session:
        validate_json_response(
            response,
            404,
            BaseResponse(status="error", message="Session not found.").model_dump(),
        )
    else:
        # exact same session is downloaded again
        assert response.status_code == 200
        assert json.loads(
            response.content.decode("utf8")
        ) == SessionRepository.read_to_json(test_db, session.id)


@pytest.mark.parametrize("valid_session", [True, False])
@pytest.mark.parametrize("one_sense_per_discourse", [True, False])
def test_overwrite_annotation(
    test_db: DBSession,
    client: TestClient,
    valid_session: bool,
    one_sense_per_discourse: bool,
    radio_andorra_id: int,
):
    toponyms = [
        ToponymCreate(text="Andorra", start=0, end=7),
        ToponymCreate(text="Andorra", start=22, end=29),
    ]
    session_id = uuid.uuid4()
    if valid_session:
        session = set_session(
            test_db,
            settings=SessionSettingsCreate(
                one_sense_per_discourse=one_sense_per_discourse
            ),
            toponyms=toponyms,
            text="Andorra is as nice as Andorra.",
        )
        session_id = session.id
    data = {
        "text": toponyms[0].text,
        "start": toponyms[0].start,
        "end": toponyms[0].end,
        "loc_id": radio_andorra_id,
    }
    response = client.put(
        f"/session/{session_id}/document/{0}/annotation",
        json=data,
    )
    if not valid_session:
        validate_json_response(
            response,
            404,
            BaseResponse(status="error", message="Session not found.").model_dump(),
        )
    else:
        expected = BaseResponse().model_dump()
        validate_json_response(response, 200, jsonable_encoder(expected))


@pytest.mark.parametrize("valid_session", [True, False])
def test_update_annotation(test_db: DBSession, client: TestClient, valid_session: bool):
    session_id = uuid.uuid4()
    toponyms = [ToponymCreate(text="Andorra", start=0, end=7, loc_id="123")]
    if valid_session:
        session = set_session(test_db, toponyms=toponyms)
        session_id = session.id
    data = {
        "old_start": toponyms[0].start,
        "old_end": toponyms[0].end,
        "new_text": "Andorra la Vella",
        "new_start": 0,
        "new_end": 16,
    }
    response = client.patch(
        f"/session/{session_id}/document/{0}/annotation",
        json=data,
    )
    if not valid_session:
        validate_json_response(
            response,
            404,
            BaseResponse(status="error", message="Session not found.").model_dump(),
        )
    else:
        expected = BaseResponse().model_dump()
        validate_json_response(response, 200, jsonable_encoder(expected))


@pytest.mark.parametrize("valid_session", [True, False])
def test_delete_annotation(test_db: DBSession, client: TestClient, valid_session: bool):
    session_id = uuid.uuid4()
    toponyms = [
        ToponymCreate(text="Andorra", start=0, end=7),
        ToponymCreate(text="Madrid", start=22, end=29),
    ]
    if valid_session:
        session = set_session(test_db, toponyms=toponyms)
        session_id = session.id
    data = {
        "start": toponyms[0].start,
        "end": toponyms[0].end,
    }
    response = client.delete(
        f"/session/{session_id}/document/{0}/annotation",
        params=data,
    )
    if not valid_session:
        validate_json_response(
            response,
            404,
            BaseResponse(status="error", message="Session not found.").model_dump(),
        )
    else:
        expected = BaseResponse().model_dump()
        validate_json_response(response, 200, jsonable_encoder(expected))


@pytest.mark.parametrize("valid_session", [True, False])
def test_get_session_settings(
    test_db: DBSession, client: TestClient, valid_session: bool
):
    session_id = uuid.uuid4()
    if valid_session:
        session = set_session(test_db)
        session_id = session.id
    response = client.get(
        f"/session/{session_id}/settings",
    )
    if not valid_session:
        validate_json_response(
            response,
            404,
            BaseResponse(status="error", message="Session not found.").model_dump(),
        )
    else:
        validate_json_response(response, 200, jsonable_encoder(session.settings))


@pytest.mark.parametrize("valid_session", [True, False])
def test_put_session_settings(
    test_db: DBSession, client: TestClient, valid_session: bool
):
    session_id = uuid.uuid4()
    if valid_session:
        old_settings = SessionSettingsCreate(
            one_sense_per_discourse=False, auto_close_annotation_modal=False
        )
        session = set_session(test_db, settings=old_settings)
        session_id = session.id
        # check if old settings are in place
        assert (
            SessionSettingsRepository.read(test_db, session.settings.id).model_dump(
                exclude=["id", "session_id"]
            )
            == old_settings.model_dump()
        )
    new_settings = SessionSettingsCreate(
        one_sense_per_discourse=True, auto_close_annotation_modal=True
    )
    response = client.put(
        f"/session/{session_id}/settings",
        json=jsonable_encoder(new_settings),
    )
    if not valid_session:
        validate_json_response(
            response,
            404,
            BaseResponse(status="error", message="Session not found.").model_dump(),
        )
    else:
        validate_json_response(response, 200, BaseResponse().model_dump())
        # check if new settings are in place
        assert (
            SessionSettingsRepository.read(test_db, session.settings.id).model_dump(
                exclude=["id", "session_id"]
            )
            == new_settings.model_dump()
        )
