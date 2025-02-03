import typing as t
import uuid

from sqlalchemy import UUID, Column, ForeignKey
from sqlmodel import Field, Relationship, SQLModel

if t.TYPE_CHECKING:
    from geoparser.annotator.db.models.document import Document


class ToponymBase(SQLModel):
    text: str
    start: int
    end: int
    loc_id: t.Optional[str] = ""


class Toponym(ToponymBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    document_id: uuid.UUID = Field(
        sa_column=Column(
            UUID, ForeignKey("document.id", ondelete="CASCADE"), nullable=False
        )
    )
    document: "Document" = Relationship(back_populates="toponyms")


class ToponymCreate(ToponymBase):
    pass


class ToponymUpdate(SQLModel):
    id: uuid.UUID
    document_id: t.Optional[uuid.UUID] = None
    text: t.Optional[str] = None
    start: t.Optional[int] = None
    end: t.Optional[int] = None
    loc_id: t.Optional[str] = ""
