import json
import uuid
from contextlib import nullcontext

import pytest
from fastapi.encoders import jsonable_encoder
from sqlmodel import Session as DBSession

from geoparser.annotator.db.crud import SessionRepository
from geoparser.annotator.db.models import (
    Document,
    DocumentCreate,
    Session,
    SessionCreate,
    SessionSettings,
    SessionSettingsCreate,
    SessionUpdate,
    Toponym,
    ToponymCreate,
)
from geoparser.annotator.exceptions import SessionNotFoundException


@pytest.mark.parametrize("nested", [True, False])
def test_create(test_db: DBSession, nested: bool):
    session_create = SessionCreate(gazetteer="geonames")
    if nested:
        session_create.documents = [
            DocumentCreate(
                filename="test.txt",
                spacy_model="en_core_web_sm",
                text="Andorra is nice.",
                toponyms=[ToponymCreate(text="Andorra", start=0, end=6)],
            )
        ]
    session = SessionRepository.create(test_db, session_create)
    db_session = SessionRepository.read(test_db, session.id)
    assert type(session) is Session
    assert type(db_session) is Session
    assert db_session.model_dump(
        exclude=["id", "created_at", "last_updated"]
    ) == session_create.model_dump(
        exclude=["created_at", "last_updated", "documents", "settings"]
    )
    assert type(db_session.settings) is SessionSettings
    assert (
        db_session.settings.model_dump(exclude=["id", "session_id"])
        == SessionSettingsCreate().model_dump()
    )
    assert len(db_session.documents) == len(session_create.documents)
    if nested:
        for document in db_session.documents:
            assert type(document) is Document
            assert len(document.toponyms) == 1
            for toponym in document.toponyms:
                assert type(toponym) is Toponym


def test_create_from_json(test_db: DBSession):
    session_create = SessionCreate(
        gazetteer="geonames",
        documents=[
            DocumentCreate(
                filename="test.txt",
                spacy_model="en_core_web_sm",
                text="Andorra is nice.",
                toponyms=[ToponymCreate(text="Andorra", start=0, end=6)],
            )
        ],
    )
    session = SessionRepository.create_from_json(
        test_db, json.dumps(jsonable_encoder(session_create))
    )
    db_session = SessionRepository.read(test_db, session.id)
    assert type(session) is Session
    assert type(db_session) is Session
    assert db_session.model_dump(
        exclude=["id", "created_at", "last_updated"]
    ) == session_create.model_dump(
        exclude=["created_at", "last_updated", "documents", "settings"]
    )
    assert type(db_session.settings) is SessionSettings
    assert (
        db_session.settings.model_dump(exclude=["id", "session_id"])
        == SessionSettingsCreate().model_dump()
    )
    assert len(db_session.documents) == len(session_create.documents)
    for document in db_session.documents:
        assert type(document) is Document
        assert len(document.toponyms) == 1
        for toponym in document.toponyms:
            assert type(toponym) is Toponym


@pytest.mark.parametrize("valid_id", [True, False])
def test_read(test_db: DBSession, valid_id: bool):
    # setup: create a session
    session_id = uuid.uuid4()
    if valid_id:
        session_create = SessionCreate(
            gazetteer="geonames",
            documents=[
                DocumentCreate(
                    filename="test.txt",
                    spacy_model="en_core_web_sm",
                    text="Andorra is nice.",
                    toponyms=[ToponymCreate(text="Andorra", start=0, end=6)],
                )
            ],
        )
        session = SessionRepository.create(test_db, session_create)
        session_id = session.id
    # read session
    with nullcontext() if valid_id else pytest.raises(SessionNotFoundException):
        db_session = SessionRepository.read(test_db, session_id)
        assert type(session) is Session
        assert type(db_session) is Session
        assert db_session.model_dump(
            exclude=["id", "created_at", "last_updated"]
        ) == session_create.model_dump(
            exclude=["created_at", "last_updated", "documents", "settings"]
        )
        assert type(db_session.settings) is SessionSettings
        assert (
            db_session.settings.model_dump(exclude=["id", "session_id"])
            == SessionSettingsCreate().model_dump()
        )
        assert len(db_session.documents) == len(session_create.documents)
        for document in db_session.documents:
            assert type(document) is Document
            assert len(document.toponyms) == 1
            for toponym in document.toponyms:
                assert type(toponym) is Toponym


@pytest.mark.parametrize("valid_id", [True, False])
def test_read_to_json(test_db: DBSession, valid_id: bool):
    # setup: create a session
    session_id = uuid.uuid4()
    if valid_id:
        session_create = SessionCreate(
            gazetteer="geonames",
            documents=[
                DocumentCreate(
                    filename="test.txt",
                    spacy_model="en_core_web_sm",
                    text="Andorra is nice.",
                    toponyms=[ToponymCreate(text="Andorra", start=0, end=6)],
                )
            ],
        )
        session = SessionRepository.create(test_db, session_create)
        session_id = session.id
    # read session
    with nullcontext() if valid_id else pytest.raises(SessionNotFoundException):
        db_session = SessionRepository.read_to_json(test_db, session_id)
        assert type(db_session) is dict
        assert "settings" not in db_session.keys()
        assert len(db_session["documents"]) == len(session_create.documents)
        for document_dict in db_session["documents"]:
            assert len(document_dict["toponyms"]) == 1
        del db_session["created_at"]
        del db_session["last_updated"]
        del db_session["documents"]
        assert db_session == jsonable_encoder(
            session_create.model_dump(
                exclude=["created_at", "last_updated", "documents", "settings"]
            )
        )


def test_read_all(test_db: DBSession):
    session_create = SessionCreate(gazetteer="geonames")
    # with a single item in the db, only this item is returned
    first_db_session = SessionRepository.create(test_db, session_create)
    result_after_first = SessionRepository.read_all(test_db)
    assert len(result_after_first) == 1
    for elem in result_after_first:
        assert type(elem) is Session
        assert elem.id == first_db_session.id
    # with multiple items in the db, all are returned
    second_db_session = SessionRepository.create(test_db, session_create)
    result_after_second = SessionRepository.read_all(test_db)
    assert len(result_after_second) == 2
    for i, elem in enumerate(result_after_second):
        assert type(elem) is Session
        assert elem.id == first_db_session.id if i == 0 else second_db_session.id
    # with filtering, only the correct item is returned
    result_after_first = SessionRepository.read_all(test_db, id=first_db_session.id)
    assert len(result_after_first) == 1
    for elem in result_after_first:
        assert type(elem) is Session
        assert elem.id == first_db_session.id


@pytest.mark.parametrize("valid_id", [True, False])
def test_update(test_db: DBSession, valid_id: bool):
    # setup: create a session
    session_id = uuid.uuid4()
    if valid_id:
        session_create = SessionCreate(gazetteer="geonames")
        session = SessionRepository.create(test_db, session_create)
        session_id = session.id
    with nullcontext() if valid_id else pytest.raises(SessionNotFoundException):
        # read initial value
        db_session = SessionRepository.read(test_db, session_id)
        assert db_session.gazetteer == "geonames"
        # update and check new value
        SessionRepository.update(
            test_db, SessionUpdate(id=session_id, gazetteer="swissnames3d")
        )
        db_session = SessionRepository.read(test_db, session_id)
        assert db_session.gazetteer == "swissnames3d"


@pytest.mark.parametrize("valid_id", [True, False])
def test_delete(test_db: DBSession, valid_id: bool):
    # setup: create a session
    session_id = uuid.uuid4()
    if valid_id:
        session_create = SessionCreate(gazetteer="geonames")
        session = SessionRepository.create(test_db, session_create)
        session_id = session.id
    with nullcontext() if valid_id else pytest.raises(SessionNotFoundException):
        # session exists initially
        assert SessionRepository.read(test_db, session_id)
        SessionRepository.delete(test_db, session_id)
    # session does not exist after deletion
    with pytest.raises(SessionNotFoundException):
        assert SessionRepository.read(test_db, session_id)
