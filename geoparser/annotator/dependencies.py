import typing as t
import uuid

from fastapi import Depends
from sqlmodel import Session as DBSession

from geoparser.annotator.db.crud import SessionRepository
from geoparser.annotator.db.db import get_db
from geoparser.annotator.exceptions import (
    DocumentNotFoundException,
    SessionNotFoundException,
)


def _get_session(db: t.Annotated[DBSession, Depends(get_db)], session_id: str):
    return SessionRepository.read(db, uuid.UUID(session_id))


def get_session(session: t.Annotated[dict, Depends(_get_session)]):
    if not session:
        raise SessionNotFoundException
    return session


def _get_document(session: t.Annotated[dict, Depends(_get_session)], doc_index: int):
    if session is not None and doc_index < len(session.documents):
        return session.documents[doc_index]


def get_document(session: t.Annotated[dict, Depends(get_session)], doc_index: int):
    if doc_index >= len(session.documents):
        raise DocumentNotFoundException
    return session.documents[doc_index]
