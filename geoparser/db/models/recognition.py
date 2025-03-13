import typing as t
import uuid

from sqlalchemy import UUID, Column, ForeignKey
from sqlmodel import Field, Relationship, SQLModel

if t.TYPE_CHECKING:
    from geoparser.db.models.recognition_module import RecognitionModule
    from geoparser.db.models.toponym import Toponym


class RecognitionBase(SQLModel):
    """Base model for the recognition process."""

    module_id: uuid.UUID = Field(
        sa_column=Column(
            UUID, ForeignKey("recognitionmodule.id", ondelete="CASCADE"), nullable=False
        )
    )


class Recognition(RecognitionBase, table=True):
    """
    Records which recognition processes identified each toponym.

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
    module: "RecognitionModule" = Relationship(back_populates="recognitions")


class RecognitionCreate(RecognitionBase):
    """Model for creating a new recognition record."""

    pass


class RecognitionUpdate(SQLModel):
    """Model for updating a recognition record."""

    id: uuid.UUID
    toponym_id: t.Optional[uuid.UUID] = None
    module_id: t.Optional[uuid.UUID] = None
