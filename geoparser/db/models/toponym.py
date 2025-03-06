import typing as t
import uuid

from sqlalchemy import UUID, Column, ForeignKey
from sqlmodel import Field, Relationship, SQLModel

if t.TYPE_CHECKING:
    from geoparser.db.models.document import Document
    from geoparser.db.models.location import Location
    from geoparser.db.models.recognition_module import RecognitionModule


class ToponymBase(SQLModel):
    start: int
    end: int


class Toponym(ToponymBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    document_id: uuid.UUID = Field(
        sa_column=Column(
            UUID, ForeignKey("document.id", ondelete="CASCADE"), nullable=False
        )
    )
    document: "Document" = Relationship(back_populates="toponyms")
    locations: list["Location"] = Relationship(
        back_populates="toponym",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
        },
    )
    recognitions: list["RecognitionModule"] = Relationship(
        back_populates="toponym",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
        },
    )


class ToponymCreate(ToponymBase):
    pass


class ToponymUpdate(SQLModel):
    id: uuid.UUID
    document_id: t.Optional[uuid.UUID] = None
    start: t.Optional[int] = None
    end: t.Optional[int] = None
