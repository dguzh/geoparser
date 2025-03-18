import typing as t
import uuid

from sqlalchemy import UUID, Column, ForeignKey
from sqlmodel import Field, Relationship, SQLModel

if t.TYPE_CHECKING:
    from geoparser.db.models.document import Document
    from geoparser.db.models.location import Location
    from geoparser.db.models.recognition import Recognition
    from geoparser.db.models.resolution_process import ResolutionProcess


class ToponymBase(SQLModel):
    """Base model for toponym data."""

    start: int  # Start position of the toponym in the document text
    end: int  # End position of the toponym in the document text


class Toponym(ToponymBase, table=True):
    """
    Represents a toponym (place name) identified in a document.

    A toponym is a place name found in text, defined by its start and end positions.
    It can have multiple potential location interpretations (resolved locations).
    """

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
    recognitions: list["Recognition"] = Relationship(
        back_populates="toponym",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
        },
    )
    resolution_processes: list["ResolutionProcess"] = Relationship(
        back_populates="toponym",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
        },
    )


class ToponymCreate(ToponymBase):
    """
    Model for creating a new toponym.

    Includes the document_id to associate the toponym with a document.
    """

    document_id: uuid.UUID


class ToponymUpdate(SQLModel):
    """Model for updating an existing toponym."""

    id: uuid.UUID
    document_id: t.Optional[uuid.UUID] = None
    start: t.Optional[int] = None
    end: t.Optional[int] = None
