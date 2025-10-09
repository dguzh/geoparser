import typing as t
import uuid

from sqlalchemy import UUID, Column, ForeignKey, String
from sqlmodel import Field, Relationship, SQLModel

if t.TYPE_CHECKING:
    from geoparser.db.models.document import Document
    from geoparser.db.models.recognizer import Recognizer


class RecognitionBase(SQLModel):
    """Base model for recognition data."""


class Recognition(RecognitionBase, table=True):
    """
    Tracks which documents have been processed by which recognizers.

    This allows tracking of which recognizers have already processed a document,
    even if no names were found.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    document_id: uuid.UUID = Field(
        sa_column=Column(
            UUID, ForeignKey("document.id", ondelete="CASCADE"), nullable=False
        )
    )
    recognizer_id: str = Field(
        sa_column=Column(
            String, ForeignKey("recognizer.id", ondelete="CASCADE"), nullable=False
        )
    )
    document: "Document" = Relationship(back_populates="recognitions")
    recognizer: "Recognizer" = Relationship(back_populates="recognitions")


class RecognitionCreate(RecognitionBase):
    """Model for creating a new recognition record."""

    document_id: uuid.UUID
    recognizer_id: str


class RecognitionUpdate(SQLModel):
    """Model for updating an existing recognition record."""

    id: uuid.UUID
    document_id: t.Optional[uuid.UUID] = None
    recognizer_id: t.Optional[str] = None
