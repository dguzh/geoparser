import typing as t
import uuid

from fastapi import Depends
from sqlmodel import Session as DBSession

from geoparser.annotator.db.crud import SessionRepository
from geoparser.annotator.db.db import get_db
from geoparser.annotator.db.models import AnnotatorDocument, AnnotatorSession
from geoparser.annotator.exceptions import DocumentNotFoundException


def get_session(
    db: t.Annotated[DBSession, Depends(get_db)], session_id: uuid.UUID
) -> AnnotatorSession:
    return SessionRepository.read(db, session_id)


def get_document(
    session: t.Annotated[AnnotatorSession, Depends(get_session)], doc_index: int
) -> AnnotatorDocument:
    if doc_index < len(session.documents):
        return session.documents[doc_index]
    else:
        raise DocumentNotFoundException
