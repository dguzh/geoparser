import typing as t
import uuid
from datetime import datetime

from sqlmodel import Field, Relationship, SQLModel

from geoparser.annotator.db.models.settings import SessionSettingsCreate

if t.TYPE_CHECKING:
    from geoparser.annotator.db.models.document import Document, DocumentCreate
    from geoparser.annotator.db.models.settings import SessionSettings


class SessionBase(SQLModel):
    created_at: datetime = Field(default_factory=datetime.now)
    last_updated: datetime = Field(default_factory=datetime.now)
    gazetteer: str


class Session(SessionBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    settings: "SessionSettings" = Relationship(back_populates="session")
    documents: list["Document"] = Relationship(back_populates="session")


class SessionCreate(SessionBase):
    settings: "SessionSettingsCreate" = SessionSettingsCreate()
    documents: t.Optional[list["DocumentCreate"]] = []


class SessionUpdate(SQLModel):
    id: uuid.UUID
    created_at: t.Optional[datetime] = None
    last_updated: t.Optional[datetime] = None
    gazetteer: t.Optional[str] = None
