import typing as t
import uuid

from sqlalchemy import UUID, Column, ForeignKey
from sqlmodel import Field, Relationship, SQLModel

if t.TYPE_CHECKING:
    from geoparser.db.models.toponym import Toponym


class RecognitionModuleBase(SQLModel):
    """Base model for the recognition module bridging table."""

    recognition_module: (
        str  # Name of the recognition module that identified this toponym
    )


class RecognitionModule(RecognitionModuleBase, table=True):
    """
    Bridging table that tracks which recognition modules identified each toponym.

    This allows a single toponym to be recognized by multiple modules without
    creating duplicate toponym entries.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    toponym_id: uuid.UUID = Field(
        sa_column=Column(
            UUID, ForeignKey("toponym.id", ondelete="CASCADE"), nullable=False
        )
    )
    toponym: "Toponym" = Relationship(back_populates="recognitions")


class RecognitionModuleCreate(RecognitionModuleBase):
    """Model for creating a new recognition module record."""

    pass


class RecognitionModuleUpdate(SQLModel):
    """Model for updating a recognition module record."""

    id: uuid.UUID
    toponym_id: t.Optional[uuid.UUID] = None
    recognition_module: t.Optional[str] = None
