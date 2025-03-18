import typing as t
import uuid

from sqlalchemy import UUID, Column, ForeignKey
from sqlmodel import Field, Relationship, SQLModel

if t.TYPE_CHECKING:
    from geoparser.db.models.document import Document
    from geoparser.db.models.recognition_module import RecognitionModule


class RecognitionProcessBase(SQLModel):
    """
    Base model for recognition process data.

    Records that a document was processed by a specific recognition module,
    regardless of whether any toponyms were found.
    """

    document_id: uuid.UUID = Field(
        sa_column=Column(
            UUID, ForeignKey("document.id", ondelete="CASCADE"), nullable=False
        )
    )
    module_id: uuid.UUID = Field(
        sa_column=Column(
            UUID, ForeignKey("recognitionmodule.id", ondelete="CASCADE"), nullable=False
        )
    )


class RecognitionProcess(RecognitionProcessBase, table=True):
    """
    Represents a recognition process.

    Tracks that a document was processed by a specific recognition module,
    even if no toponyms were found.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    document: "Document" = Relationship(back_populates="recognition_processes")
    module: "RecognitionModule" = Relationship(back_populates="recognition_processes")


class RecognitionProcessCreate(RecognitionProcessBase):
    """Model for creating a new recognition process record."""


class RecognitionProcessUpdate(SQLModel):
    """Model for updating an existing recognition process record."""

    id: uuid.UUID
    document_id: t.Optional[uuid.UUID] = None
    module_id: t.Optional[uuid.UUID] = None 