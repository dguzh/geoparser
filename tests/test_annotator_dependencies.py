import uuid
from contextlib import nullcontext

import pytest
from sqlmodel import Session as DBSession

from geoparser.annotator.db.crud import SessionRepository
from geoparser.annotator.db.models import DocumentCreate, SessionCreate, ToponymCreate
from geoparser.annotator.dependencies import get_document, get_session
from geoparser.annotator.exceptions import (
    DocumentNotFoundException,
    SessionNotFoundException,
)


@pytest.mark.parametrize("valid_session", [True, False])
def test_get_session(test_db: DBSession, valid_session: bool):
    session_id = uuid.uuid4()
    if valid_session:
        session = SessionRepository.create(
            test_db,
            SessionCreate(
                gazetteer="geonames",
                documents=[
                    DocumentCreate(
                        filename="test.txt",
                        spacy_model="en_core_web_sm",
                        text="Andorra is nice.",
                        toponyms=[ToponymCreate(text="Andorra", start=0, end=7)],
                    )
                ],
            ),
        )
        session_id = session.id
    with nullcontext() if valid_session else pytest.raises(SessionNotFoundException):
        assert get_session(test_db, session_id).model_dump() == session.model_dump()


@pytest.mark.parametrize("doc_index", [0, 1])  # doc_index 1 is invalid
def test_get_document(test_db: DBSession, doc_index: int):
    session = SessionRepository.create(
        test_db,
        SessionCreate(
            gazetteer="geonames",
            documents=[
                DocumentCreate(
                    filename="test.txt",
                    spacy_model="en_core_web_sm",
                    text="Andorra is nice.",
                    toponyms=[ToponymCreate(text="Andorra", start=0, end=7)],
                )
            ],
        ),
    )
    with nullcontext() if doc_index == 0 else pytest.raises(DocumentNotFoundException):
        assert (
            get_document(session, doc_index).model_dump()
            == session.documents[doc_index].model_dump()
        )
