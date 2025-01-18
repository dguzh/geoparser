import typing as t
import uuid
from datetime import datetime

from sqlmodel import Field, Relationship, SQLModel, ForeignKey
from sqlalchemy.orm import RelationshipProperty

if t.TYPE_CHECKING:
    from geoparser.annotator.db.models.document import Document
    from geoparser.annotator.db.models.settings import SessionSettings


class SessionBase(SQLModel):
    created_at: t.Optional[datetime] = datetime.now()
    last_updated: t.Optional[datetime] = datetime.now()
    gazetteer: str


class Session(SessionBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    settings: "SessionSettings" = Relationship(
        back_populates="session", sa_relationship=ForeignKey("sessionsettings.id")
    )
    documents: list["Document"] = Relationship(
        back_populates="session",
        sa_relationship_kwargs={
            "order_by": "asc(Document.doc_index)",
            "foreign_keys": "Document.id",
        },
    )


class SessionCreate(SessionBase):
    pass


class SessionGet(SessionBase):
    id: uuid.UUID


class SessionUpdate(SessionGet):
    created_at: t.Optional[datetime]
    last_updated: t.Optional[datetime]
    gazetteer: t.Optional[str]
