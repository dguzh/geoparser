import typing as t
import uuid

from sqlalchemy import UUID, Column, ForeignKey
from sqlmodel import Field, Relationship, SQLModel

if t.TYPE_CHECKING:
    from geoparser.db.models.reference import Reference
    from geoparser.db.models.resolution_module import ResolutionModule


class ResolutionSubjectBase(SQLModel):
    """Base model for resolution subject data."""

    reference_id: uuid.UUID = Field(
        sa_column=Column(
            UUID, ForeignKey("reference.id", ondelete="CASCADE"), nullable=False
        )
    )
    module_id: uuid.UUID = Field(
        sa_column=Column(
            UUID, ForeignKey("resolutionmodule.id", ondelete="CASCADE"), nullable=False
        )
    )


class ResolutionSubject(ResolutionSubjectBase, table=True):
    """
    Tracks which references have been processed by which resolution modules.

    This allows tracking of which modules have already processed a reference,
    even if no locations were found.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    reference: "Reference" = Relationship(back_populates="resolution_subjects")
    module: "ResolutionModule" = Relationship(back_populates="resolution_subjects")


class ResolutionSubjectCreate(ResolutionSubjectBase):
    """Model for creating a new resolution subject record."""


class ResolutionSubjectUpdate(SQLModel):
    """Model for updating an existing resolution subject record."""

    id: uuid.UUID
    reference_id: t.Optional[uuid.UUID] = None
    module_id: t.Optional[uuid.UUID] = None
