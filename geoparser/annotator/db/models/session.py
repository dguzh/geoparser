import typing as t
import uuid
from datetime import datetime

from sqlmodel import Field, Relationship, SQLModel

if t.TYPE_CHECKING:
    from geoparser.annotator.db.models.document import Document, DocumentCreate
    from geoparser.annotator.db.models.settings import (
        SessionSettings,
        SessionSettingsCreate,
    )


class SessionBase(SQLModel):
    created_at: datetime = Field(default_factory=datetime.now)
    last_updated: datetime = Field(default_factory=datetime.now)
    gazetteer: str


class Session(SessionBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    settings: "SessionSettings" = Relationship(back_populates="session")
    documents: list["Document"] = Relationship(back_populates="session")


class SessionCreate(SessionBase):
    settings: t.Optional["SessionSettingsCreate"] = None
    documents: t.Optional[list["DocumentCreate"]] = []


class SessionGet:
    id: uuid.UUID


class SessionUpdate(SessionGet):
    created_at: t.Optional[datetime]
    last_updated: t.Optional[datetime]
    gazetteer: t.Optional[str]
