import typing as t
import uuid

from sqlalchemy import UUID, Column, ForeignKey
from sqlmodel import Field, Relationship, SQLModel

if t.TYPE_CHECKING:
    from geoparser.db.models.document import Document
    from geoparser.db.models.recognition_module import RecognitionModule


class RecognitionSubjectBase(SQLModel):
    """Base model for recognition subject data."""

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


class RecognitionSubject(RecognitionSubjectBase, table=True):
    """
    Tracks which documents have been processed by which recognition modules.

    This allows tracking of which modules have already processed a document,
    even if no toponyms were found.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    document: "Document" = Relationship(back_populates="recognition_subjects")
    module: "RecognitionModule" = Relationship(back_populates="recognition_subjects")


class RecognitionSubjectCreate(RecognitionSubjectBase):
    """Model for creating a new recognition subject record."""


class RecognitionSubjectUpdate(SQLModel):
    """Model for updating an existing recognition subject record."""

    id: uuid.UUID
    document_id: t.Optional[uuid.UUID] = None
    module_id: t.Optional[uuid.UUID] = None
