import typing as t
import uuid

from pydantic import AfterValidator
from sqlalchemy import UUID, Column, ForeignKey
from sqlmodel import Field, Relationship, SQLModel

from geoparser.db.models.validators import normalize_newlines

if t.TYPE_CHECKING:
    from geoparser.db.models.session import Session
    from geoparser.db.models.toponym import Toponym, ToponymCreate


class DocumentBase(SQLModel):
    text: t.Annotated[str, AfterValidator(normalize_newlines)]


class Document(DocumentBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    session_id: uuid.UUID = Field(
        sa_column=Column(
            UUID, ForeignKey("session.id", ondelete="CASCADE"), nullable=False
        )
    )
    session: "Session" = Relationship(back_populates="documents")
    toponyms: list["Toponym"] = Relationship(
        back_populates="document",
        sa_relationship_kwargs={
            "order_by": "Toponym.start",
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
        },
    )


class DocumentCreate(DocumentBase):
    toponyms: t.Optional[list["ToponymCreate"]] = []


class DocumentUpdate(SQLModel):
    id: uuid.UUID
    text: t.Optional[str] = None
