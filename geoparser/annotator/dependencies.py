import typing as t
import uuid

from fastapi import Depends
from sqlmodel import Session as DBSession

from geoparser.annotator.exceptions import DocumentNotFoundException
from geoparser.db.crud import SessionRepository
from geoparser.db.db import get_db
from geoparser.db.models import Document, Session


def get_session(
    db: t.Annotated[DBSession, Depends(get_db)], session_id: uuid.UUID
) -> Session:
    return SessionRepository.read(db, session_id)


def get_document(
    session: t.Annotated[Session, Depends(get_session)], doc_index: int
) -> Document:
    if doc_index < len(session.documents):
        return session.documents[doc_index]
    else:
        raise DocumentNotFoundException
