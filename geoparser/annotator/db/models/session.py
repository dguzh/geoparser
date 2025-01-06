import typing as t
from datetime import datetime
from sqlmodel import SQLModel, Relationship, Field
from pydantic import BaseModel, field_validator

from geoparser.annotator.db.models.document import Document
from geoparser.annotator.db.models.settings import SessionSettings


class Session(SQLModel, table=True):
    id: t.Optional[int] = Field(default=None, primary_key=True)
    session_id: str
    created_at: t.Optional[datetime] = datetime.now()
    last_updated: t.Optional[datetime] = datetime.now()
    gazetteer: str
    toponyms: list[SessionSettings] = Relationship(back_populates="session")
    documents: list[Document] = Relationship(back_populates="session")

    # @field_validator("documents", mode="after")
    # @classmethod
    # def sort_documents(cls, value: list[Document]) -> list[Document]:
    #     return sorted(value, key=lambda x: x.doc_index)
