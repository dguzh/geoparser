import typing as t
import uuid

from sqlalchemy import UUID, Column, ForeignKey
from sqlmodel import Field, Relationship, SQLModel

if t.TYPE_CHECKING:
    from geoparser.db.models.toponym import Toponym
    from geoparser.db.models.recognition_module import RecognitionModule


class RecognitionObjectBase(SQLModel):
    """Base model for recognition object data."""
    
    toponym_id: uuid.UUID = Field(
        sa_column=Column(
            UUID, ForeignKey("toponym.id", ondelete="CASCADE"), nullable=False
        )
    )
    module_id: uuid.UUID = Field(
        sa_column=Column(
            UUID, ForeignKey("recognitionmodule.id", ondelete="CASCADE"), nullable=False
        )
    )


class RecognitionObject(RecognitionObjectBase, table=True):
    """
    Represents a recognition object.

    Tracks which recognition module identified a specific toponym.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    toponym: "Toponym" = Relationship(back_populates="recognition_objects")
    module: "RecognitionModule" = Relationship(back_populates="recognition_objects")


class RecognitionObjectCreate(RecognitionObjectBase):
    """Model for creating a new recognition object."""


class RecognitionObjectUpdate(SQLModel):
    """Model for updating an existing recognition object."""

    id: uuid.UUID
    toponym_id: t.Optional[uuid.UUID] = None
    module_id: t.Optional[uuid.UUID] = None
