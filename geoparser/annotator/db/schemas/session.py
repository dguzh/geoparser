import typing as t
from datetime import datetime

from pydantic import BaseModel, field_validator

from geoparser.annotator.db.schemas.document import Document
from geoparser.annotator.db.schemas.settings import SessionSettings


class Session(BaseModel):
    session_id: str
    created_at: t.Optional[datetime] = datetime.now()
    last_updated: t.Optional[datetime] = datetime.now()
    gazetteer: str
    settings: t.Optional[SessionSettings] = SessionSettings()
    documents: t.Optional[list[Document]] = []

    @field_validator("toponyms", mode="after")
    @classmethod
    def sort_documents(cls, value: list[Document]) -> list[Document]:
        return sorted(value, key=lambda x: x.doc_index)
