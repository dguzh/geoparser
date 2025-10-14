import typing as t
import uuid

from sqlalchemy import UUID, Column, ForeignKey
from sqlmodel import Field, Relationship, SQLModel

if t.TYPE_CHECKING:
    from geoparser.annotator.db.models.document import AnnotatorDocument


class AnnotatorToponymBase(SQLModel):
    text: str
    start: int
    end: int
    loc_id: t.Optional[str] = ""


class AnnotatorToponym(AnnotatorToponymBase, table=True):
    __tablename__ = "annotatortoponym"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    document_id: uuid.UUID = Field(
        sa_column=Column(
            UUID, ForeignKey("annotatordocument.id", ondelete="CASCADE"), nullable=False
        )
    )
    document: "AnnotatorDocument" = Relationship(back_populates="toponyms")


class AnnotatorToponymCreate(AnnotatorToponymBase):
    pass


class AnnotatorToponymUpdate(SQLModel):
    id: uuid.UUID
    document_id: t.Optional[uuid.UUID] = None
    text: t.Optional[str] = None
    start: t.Optional[int] = None
    end: t.Optional[int] = None
    loc_id: t.Optional[str] = ""
