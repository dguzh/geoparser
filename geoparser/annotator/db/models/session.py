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
    settings: "SessionSettings" = Relationship(
        back_populates="session",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
        },
    )
    documents: list["Document"] = Relationship(
        back_populates="session",
        sa_relationship_kwargs={
            "order_by": "Document.doc_index",
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
        },
    )


class SessionCreate(SessionBase):
    settings: "SessionSettingsCreate" = SessionSettingsCreate()
    documents: t.Optional[list["DocumentCreate"]] = []


class SessionDownload(SessionBase):
    documents: t.Optional[list["DocumentCreate"]] = []


class SessionForTemplate(SessionBase):
    id: uuid.UUID
    num_documents: int


class SessionUpdate(SQLModel):
    id: uuid.UUID
    created_at: t.Optional[datetime] = None
    last_updated: t.Optional[datetime] = None
    gazetteer: t.Optional[str] = None
