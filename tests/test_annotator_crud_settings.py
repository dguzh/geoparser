import uuid
from contextlib import nullcontext

import pytest
from sqlmodel import Session as DBSession

from geoparser.annotator.db.crud import SessionRepository, SessionSettingsRepository
from geoparser.annotator.db.models import (
    SessionCreate,
    SessionSettings,
    SessionSettingsCreate,
    SessionSettingsUpdate,
)
from geoparser.annotator.exceptions import SessionSettingsNotFoundException


@pytest.mark.parametrize("valid_id", [True, False])
def test_create(test_db: DBSession, valid_id: bool):
    # setup: create a session to link the settings to
    session_create = SessionCreate(gazetteer="geonames")
    session = SessionRepository.create(test_db, session_create)
    settings_id = uuid.uuid4()
    if valid_id:
        # create settings
        settings_create = SessionSettingsCreate()
        settings = SessionSettingsRepository.create(
            test_db, settings_create, additional={"session_id": session.id}
        )
        settings_id = settings.id
    with nullcontext() if valid_id else pytest.raises(SessionSettingsNotFoundException):
        db_settings = SessionSettingsRepository.read(test_db, settings_id)
        assert type(db_settings) is SessionSettings
        assert (
            db_settings.model_dump(exclude=["id", "session_id"])
            == settings_create.model_dump()
        )


@pytest.mark.parametrize("valid_id", [True, False])
def test_read(test_db: DBSession, valid_id: bool):
    # setup: create a session to link the settings to
    session_create = SessionCreate(gazetteer="geonames")
    session = SessionRepository.create(test_db, session_create)
    settings_id = uuid.uuid4()
    if valid_id:
        settings_create = SessionSettingsCreate()
        settings = SessionSettingsRepository.create(
            test_db, settings_create, additional={"session_id": session.id}
        )
        settings_id = settings.id
    with nullcontext() if valid_id else pytest.raises(SessionSettingsNotFoundException):
        db_settings = SessionSettingsRepository.read(test_db, settings_id)
        assert type(db_settings) is SessionSettings
        assert (
            db_settings.model_dump(exclude=["id", "session_id"])
            == settings_create.model_dump()
        )


def test_read_all(test_db: DBSession):
    # setup: create a session (with included settings)
    session_create = SessionCreate(gazetteer="geonames")
    session = SessionRepository.create(test_db, session_create)
    result_after_first = SessionSettingsRepository.read_all(test_db)
    assert len(result_after_first) == 1
    assert type(result_after_first[0]) is SessionSettings
    assert result_after_first[0].id == session.settings.id
    # with multiple items in the db, all are returned
    second_session = SessionRepository.create(test_db, session_create)
    result_after_second = SessionSettingsRepository.read_all(test_db)
    assert len(result_after_second) == 2
    for i, elem in enumerate(result_after_second):
        assert type(elem) is SessionSettings
        assert elem.id == session.settings.id if i == 0 else second_session.settings.id
    # with filtering, only the correct item is returned
    results = SessionSettingsRepository.read_all(test_db, id=session.settings.id)
    assert len(results) == 1
    assert type(results[0]) is SessionSettings
    assert results[0].id == session.settings.id


@pytest.mark.parametrize("valid_id", [True, False])
def test_update(test_db: DBSession, valid_id: bool):
    # setup: create a session (with included settings)
    session_create = SessionCreate(gazetteer="geonames")
    session = SessionRepository.create(test_db, session_create)
    settings_id = uuid.uuid4()
    if valid_id:
        settings_create = SessionSettingsCreate()
        settings = SessionSettingsRepository.create(
            test_db, settings_create, additional={"session_id": session.id}
        )
        settings_id = settings.id
    with nullcontext() if valid_id else pytest.raises(SessionSettingsNotFoundException):
        # read initial value
        db_settings = SessionSettingsRepository.read(test_db, settings_id)
        assert (
            db_settings.one_sense_per_discourse
            == settings_create.one_sense_per_discourse
            == False  # False is default
        )
        # update and check new value
        SessionSettingsRepository.update(
            test_db, SessionSettingsUpdate(id=settings_id, one_sense_per_discourse=True)
        )
        db_settings = SessionSettingsRepository.read(test_db, settings_id)
        assert db_settings.one_sense_per_discourse is True


@pytest.mark.parametrize("valid_id", [True, False])
def test_delete(test_db: DBSession, valid_id: bool):
    # setup: create a session (with included settings)
    session_create = SessionCreate(gazetteer="geonames")
    session = SessionRepository.create(test_db, session_create)
    settings_id = uuid.uuid4()
    if valid_id:
        settings_create = SessionSettingsCreate()
        settings = SessionSettingsRepository.create(
            test_db, settings_create, additional={"session_id": session.id}
        )
        settings_id = settings.id
    with nullcontext() if valid_id else pytest.raises(SessionSettingsNotFoundException):
        # settings exists initially
        assert SessionSettingsRepository.read(test_db, settings_id)
        SessionSettingsRepository.delete(test_db, settings_id)
    # settings does not exist after deletion
    with pytest.raises(SessionSettingsNotFoundException):
        SessionSettingsRepository.read(test_db, settings_id)
